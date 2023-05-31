import os
import re
import textwrap
from datetime import datetime
from typing import Optional, List, Mapping, Any
from utils import Markdown
from langchain import PromptTemplate, OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chains.router import MultiPromptChain
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.chains.router.multi_prompt_prompt import MULTI_PROMPT_ROUTER_TEMPLATE
from langchain.chat_models.base import BaseChatModel, SimpleChatModel
from langchain.llms.base import LLM
from Levenshtein import distance
from langchain.schema import BaseMessage
import inspect


class LLMLogger:
    """
    Logs the requests and responses to a file, to be able to analyze the performance of the model.
    """
    def __init__(self, llm: LLM):
        self.llm = llm

    @staticmethod
    def log_request(model: str, prompt: str, reply: str):

        calls_log = os.path.join(os.getcwd(), "open_ai_calls.log")
        f = open(calls_log, 'a')

        # Current time to log
        time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        f.write(f"<request model='{model}' time='{time}'>\n")
        f.write(prompt)
        f.write('\n')
        f.write('</request>\n')
        f.write('<response>\n')
        f.write(reply)
        f.write('\n')
        f.write('</response>\n')
        f.write('\n\n')
        f.close()


class LoggerLLMModel(LLM):
    import langchain
    llm: langchain.llms.openai.OpenAI

    @property
    def _llm_type(self) -> str:
        return "custom"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:

        reply = self.llm(prompt)
        LLMLogger.log_request(self.llm.model_name, prompt, reply)

        return reply


class LoggerChatModel(SimpleChatModel):
    import langchain
    llm: langchain.chat_models.openai.ChatOpenAI

    @property
    def _llm_type(self) -> str:
        return "custom"

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
    ) -> str:

        reply = self.llm.generate([messages], stop=stop, callbacks=run_manager)
        LLMLogger.log_request(self.llm.model_name, str(messages), str(reply.generations))

        return reply.generations[0][0].text


class GPTAnswerer:
    # TODO: template = textwrap.dedent(template) all templates
    def __init__(self, resume: str, personal_data: str, cover_letter: str, job_filtering_rules: str):
        """
        Initializes the GPTAnswerer.
        :param resume: The resume text, preferably in Markdown format.
        :param personal_data: The personal data text, preferably in Markdown format, following the template, but any text is fine.
        :param cover_letter: The cover letter text, preferably in Markdown format, use placeholders as [position], [company], etc.
        """
        self.resume = resume
        self.personal_data = personal_data
        self.cover_letter = cover_letter
        self._job_description = ""
        self.job_description_summary = ""
        self.job_filtering_rules = job_filtering_rules
        '''
        Two lists of job titles, a whitelist and a blacklist.
        ```
        Titles whitelist: Something, Something else, Another thing  
        Titles blacklist: I don't want this, I don't want that
        ``` 
        '''

        # Wrapping the models on a logger to log the requests and responses
        self.llm = LoggerChatModel(llm=ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=GPTAnswerer.openai_api_key(), temperature=0.5))
        self.llm_basic = LoggerLLMModel(llm=OpenAI(model_name="text-curie-001", openai_api_key=GPTAnswerer.openai_api_key(), temperature=0.5))
        self.llm_advanced = LoggerLLMModel(llm=OpenAI(model_name="text-davinci-003", openai_api_key=GPTAnswerer.openai_api_key(), temperature=0.5))

    @property
    def job_description(self):
        return self._job_description

    @job_description.setter
    def job_description(self, value):
        self._job_description = value
        self.job_description_summary = self.summarize_job_description(value)

    @staticmethod
    def openai_api_key():
        """
        Returns the OpenAI API key.
        environment variable used: OPEN_AI_API_KEY
        Returns: The OpenAI API key.
        """
        key = os.getenv('OPEN_AI_API_KEY')

        if key is None:
            raise Exception("OpenAI API key not found. Please set the OPEN_AOI_API_KEY environment variable.")

        return key

    def summarize_job_description(self, text: str) -> str:
        """
        Summarizes the text using the OpenAI API.
        Args:
            text: The text to summarize.
        Returns:
            The summarized text.
        """
        summarize_prompt_template = """
        The following is a summarized job description, following the rules and the template below.
        
        # Rules
        - Remove boilerplate text
        - Only relevant information to match the job description against the resume.
                
        # Job Description:
        ```
        {text}
        ```
        
        ---
        
        # Job Description Summary"""
        prompt = PromptTemplate(input_variables=["text"], template=summarize_prompt_template)  # Define the prompt (template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        output = chain.run(text=text)

        # Remove all spaces after new lines, until no more spaces are found
        while "\n " in output:
            output = output.replace("\n ", "\n")

        return output

    def answer_question_textual_wide_range(self, question: str) -> str:
        """
        Answers a question using the resume, personal data, cover letter, and job description.
        :param question: The question to answer.
        """
        # Can answer questions from the resume, personal data, and cover letter. Deciding which context is relevant. So we don't create a very large prompt concatenating all the data.
        # Prompt templates:
        # - Resume stuff + Personal data.
        # - Cover letter -> personalize to the job description
        # - Summary -> Resume stuff + Job description (summary)

        # Templates:
        # - Resume Stuff
        resume_stuff_template = """
        The following is a resume, personal data, and an answered question using this information, being answered by the person who's resume it is (first person).
        
        ## Rules
        - Answer questions directly (if possible)
        - If seems likely that you have the experience, even if is not explicitly defined, answer as if you have the experience
        - If you cannot answer the question, answer things like "I have no experience with that, but I learn fast, very fast", "not yet, but I will learn"...
        - The answer must not be longer than a tweet (140 characters)
        - Only add periods if the answer has multiple sentences/paragraphs
        
        ## Example 1
        Resume: I'm a software engineer with 10 years of experience on both swift and python.
        Question: What is your experience with swift?
        Answer: 10 years
        
        ## Example 2
        Resume: Mick Jagger. I'm a software engineer with 4 years of experience on both C++ and python.
        Question: What is your full name?
        Answer: Mick Jagger
        
        -----
        
        ## Extended personal data:
        ```
        {personal_data}
        ```
        
        ## Resume:
        ```
        {resume}
        ```
                
        ## Question:
        {question}
        
        ## Answer:"""

        # - Cover Letter
        cover_letter_template = """
        Using the job description provided below, modify the cover letter to personalize it to the job and company. Replace all placeholders [[placeholder]] with the appropriate information from the job description. If there is no information to fill in a placeholder, remove it and adapt the answer accordingly. 

        If the question is "cover letter," answer with the modified cover letter. Do not change the signature name, it's the real name of the person who's resume it is, and who's answering the question (you).
        
        ## Job Description:
        ```
        {job_description}
        ```
        
        ## Cover Letter:
        ```
        {cover_letter}
        ```
        
        ## Question:
        {question}
        
        ## Answer:"""

        # - Summary
        summary_template = """
        The following is a resume, a job description, and an answered question using this information, being answered by the person who's resume it is (first person).
        
        ## Rules
        - Answer questions directly.
        - If seems likely that you have the experience, even if is not explicitly defined, answer as if you have the experience.
        - Find relations between the job description and the resume, and answer questions about that.
        - Only add periods if the answer has multiple sentences/paragraphs.

        
        ## Job Description:
        ```
        {job_description}
        ```
        
        ## Resume:
        ```
        {resume}
        ```
        
        ## Question:
        {question}
        
        ## Answer:"""

        prompt_infos = [
            {
                "name": "resume",
                "description": "Good for answering questions about job experience, skills, education, and personal data. Questions like 'experience with python', 'education', 'full name', 'social networks', 'links of interest', etc.",
                "prompt_template": resume_stuff_template
            },
            {
                "name": "cover letter",
                "description": "Addressing questions about the cover letter and personal characteristics about the role. Questions like 'cover letter', 'why do you want to work here?', etc.",
                "prompt_template": cover_letter_template
            },
            {
                "name": "summary",
                "description": "Good for answering questions about the job description, and how I will fit into the company or the role. Questions like, summary of the resume, why you are a good fit, etc.",
                "prompt_template": summary_template
            }
        ]

        # Create the chains, using partials to fill in the data, as the MultiPromptChain does not support more than one input variable.
        # - Resume Stuff
        resume_stuff_prompt_template = PromptTemplate(template=resume_stuff_template, input_variables=["personal_data", "resume", "question"])
        resume_stuff_prompt_template = resume_stuff_prompt_template.partial(personal_data=self.personal_data, resume=self.resume, question=question)
        resume_stuff_chain = LLMChain(
            llm=self.llm,
            prompt=resume_stuff_prompt_template
        )
        # - Cover Letter
        cover_letter_prompt_template = PromptTemplate(template=cover_letter_template, input_variables=["cover_letter", "job_description", "question"])
        cover_letter_prompt_template = cover_letter_prompt_template.partial(cover_letter=self.cover_letter, job_description=self.job_description_summary, question=question)
        cover_letter_chain = LLMChain(
            llm=self.llm,
            prompt=cover_letter_prompt_template
        )
        # - Summary
        summary_prompt_template = PromptTemplate(template=summary_template, input_variables=["resume", "job_description", "question"])
        summary_prompt_template = summary_prompt_template.partial(resume=self.resume, job_description=self.job_description_summary, question=question)
        summary_chain = LLMChain(
            llm=self.llm,
            prompt=summary_prompt_template
        )

        # Create the router chain
        destination_chains = {"resume": resume_stuff_chain, "cover letter": cover_letter_chain, "summary": summary_chain}
        default_chain = ConversationChain(llm=self.llm, output_key="text")  # Is it a ConversationChain? Or a LLMChain? Or a MultiPromptChain?
        destinations = [f"{p['name']}: {p['description']}" for p in prompt_infos]
        destinations_str = "\n".join(destinations)
        router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
            destinations=destinations_str
        )
        router_prompt = PromptTemplate(
            template=router_template,
            input_variables=["input"],
            output_parser=RouterOutputParser(),
        )

        # TODO: This is expensive. Test with new models / new versions of langchain.
        router_chain = LLMRouterChain.from_llm(self.llm_advanced, router_prompt)        # Using the advanced LLM, as is the only one that seems to work with the router chain expected output format.

        chain = MultiPromptChain(router_chain=router_chain, destination_chains=destination_chains, default_chain=resume_stuff_chain, verbose=True)

        result = chain({"input": question})
        result_text = result["text"].strip()

        # Sometimes the LLM leaves behind placeholders, we need to remove them
        result_text = self._remove_placeholders(result_text)

        return result_text

    def answer_question_textual(self, question: str) -> str:
        template = """The following is a resume and an answered question about the resume, being answered by the person who's resume it is (first person).
        
        ## Rules
        - Answer the question directly, if possible.
        - If seems likely that you have the experience based on the resume, even if is not explicit on the resume, answer as if you have the experience.
        - If you cannot answer the question, answer things like "I have no experience with that, but I learn fast, very fast", "not yet, but I will learn".
        - The answer must not be larger than a tweet (140 characters).
        - Answer questions directly. eg. "Full Name" -> "John Oliver", "Experience with python" -> "10 years"

        ## Example
        Resume: I'm a software engineer with 10 years of experience on both swift and python.
        Question: What is your experience with swift?
        Answer: 10 years.
        
        -----
        
        ## Extended personal data:
        ```
        {personal_data}
        ```
        
        ## Resume:
        ```
        {resume}
        ```
                
        ## Question:
        {question}
        
        ## Answer:"""

        prompt = PromptTemplate(input_variables=["personal_data", "resume", "question"], template=template)  # Define the prompt (template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        output = chain.run(personal_data=self.personal_data, resume=self.resume, question=question)

        return output

    def answer_question_numeric(self, question: str, default_experience: int = 0) -> int:
        template = """The following is a resume and an answered question about the resume, the answer is an integer number.
        
        ## Rules
        - The answer must be an integer number.
        - The answer must only contain digits.
        - If you cannot answer the question, answer {default_experience}.
        
        ## Example
        Resume: I'm a software engineer with 10 years of experience on swift and python.
        Question: How many years of experience do you have on swift?
        Answer: 10
        
        -----
        
        ## Extended personal data:
        ```
        {personal_data}
        ```
        
        ## Resume:
        ```
        {resume}
        ```

        ## Question:
        {question}
        
        ## Answer:"""

        prompt = PromptTemplate(input_variables=["default_experience", "personal_data", "resume", "question"], template=template)  # Define the prompt (template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        output_str = chain.run(personal_data=self.personal_data, resume=self.resume, question=question, default_experience=default_experience)

        # Convert to int with error handling
        try:
            output = int(output_str)  # Convert the output to an integer
        except ValueError:
            output = default_experience  # If the output is not an integer, return the default experience
            print(f"Error: The output of the LLM is not an integer number. The default experience ({default_experience}) will be returned instead. The output was: {output_str}")

        return output

    def answer_question_from_options(self, question: str, options: list[str]) -> str:
        template = """The following is a resume and an answered question about the resume, the answer is one of the options.
        
        ## Rules
        - The answer must be one of the options.
        - The answer must exclusively contain one of the options.
        - Answer the option that seems most likely based on the resume.
        - Never choose the default/placeholder option, examples are: 'Select an option', 'None', 'Choose from the options below', etc.
        
        ## Example
        Resume: I'm a software engineer with 10 years of experience on swift, python, C, C++.
        Question: How many years of experience do you have on python?
        Options: [1-2, 3-5, 6-10, 10+]
        Answer: 10+
        
        -----
        
        ## Extended personal data:
        ```
        {personal_data}
        ```

        ## Resume:
        ```
        {resume}
        ```

        ## Question:
        {question}
        
        ## Options:
        {options}
        
        ## Answer:"""

        prompt = PromptTemplate(input_variables=["personal_data", "resume", "question", "options"], template=template)  # Define the prompt (template)
        # formatted_prompt = prompt.format_prompt(personal_data=self.personal_data, resume=self.resume, question=question, options=options)  # Format the prompt with the data
        # output = self.llm(formatted_prompt.to_string())  # Send the prompt to the llm
        chain = LLMChain(llm=self.llm, prompt=prompt)
        output = chain.run(personal_data=self.personal_data, resume=self.resume, question=question, options=options)

        # Guard the output is one of the options
        if output not in options:
            output = self._closest_matching_option(output, options)

        return output

    @staticmethod
    def _closest_matching_option(to_match: str, options: list[str]) -> str:
        """
        Choose the closest option to the output, using a levenshtein distance.
        """
        # Choose the closest option to the output, using a levenshtein distance
        closest_option = min(options, key=lambda option: distance(to_match, option))
        return closest_option

    @staticmethod
    def _contains_placeholder(text: str) -> bool:
        """
        Check if the text contains a placeholder. A placeholder is a string like "[placeholder]".
        """
        # pattern = r"\[\w+\]"              # Matches "[placeholder]"
        pattern = r"\[\[([^\]]+)\]\]"       # Matches "[[placeholder]]"
        match = re.search(pattern, text)
        return match is not None

    def _remove_placeholders(self, text: str) -> str:
        """
        Remove the placeholder from the text, using the llm. The placeholder is a string like "[[placeholder]]".

        Does nothing if the text does not contain a placeholder.
        """
        summarize_prompt_template = """
        Following are two texts, one with placeholders and one without, the second text uses information from the first text to fill the placeholders.
        
        ## Rules
        - A placeholder is a string like "[[placeholder]]". E.g. "[[company]]", "[[job_title]]", "[[years_of_experience]]"...
        - The task is to remove the placeholders from the text.
        - If there is no information to fill a placeholder, remove the placeholder, and adapt the text accordingly.
        - No placeholders should remain in the text.
        
        ## Example
        Text with placeholders: "I'm a software engineer engineer with 10 years of experience on [placeholder] and [placeholder]."
        Text without placeholders: "I'm a software engineer with 10 years of experience."
        
        -----
        
        ## Text with placeholders:
        {text_with_placeholders}
        
        ## Text without placeholders:"""

        result = text

        # Max number of iterations to avoid infinite loops
        max_iterations = 5
        concurrent_iterations = 0

        # Remove the placeholder from the text, loop until there are no more placeholders
        while self._contains_placeholder(result) and concurrent_iterations < max_iterations:
            prompt = PromptTemplate(input_variables=["text_with_placeholders"], template=summarize_prompt_template)     # Define the prompt (template)
            chain = LLMChain(llm=self.llm, prompt=prompt)
            output = chain.run(text_with_placeholders=result)

            result = output
            concurrent_iterations += 1

        return result

    def job_title_passes_filters(self, job_title: str) -> bool:
        """
        Check if the job title passes the filters. The filters are a whitelist and a blacklist of job titles.
        :param job_title: The job title to check.
        :return: True if the job title passes the filters, False otherwise.
        """

        template = """
        The task is to determine if a given job title matches a list of job titles the user is interested in (whitelist) and a list of job titles that are not interesting (blacklist).

        # Rules:
        - Respond with either "yes" or "no". Only provide these two responses.
        - The matching process is not exhaustive; the whitelist and blacklist are merely guides.
        - Additional conditions are provided as keywords to help determine if the job title is interesting or not, but they are not exhaustive either.
        - If the "other conditions" are negative (e.g., no accounting positions), and the job title matches the negative condition (e.g., accounting positions), respond with "no".
        - Respond with "yes" if the job title is related to the whitelist, and not related to the blacklist.
        - Respond with "no" if the job title is related to the blacklist.
        - Respond with "no" if the job title is not related to the whitelist or the blacklist.
        - The job title can have more information than the position as location, industry, etc. Ignore this information.
        
        # Examples:
        ## Example 1
        Job title: "Junior Software Engineer"
        Whitelist: Software Engineer, Data Scientist, Product Manager
        Blacklist: Accounting Manager
        Other conditions: Junior positions
        Matches: no
        
        ## Example 2
        Job title: "Cashflow Manager"
        Whitelist: Data Scientist, Product Manager, Senior Software Engineer
        Blacklist: Accounting Manager
        Other conditions: 
        Matches: no
        
        ## Example 3
        Job title: "Product Manager - Healthcare"
        Whitelist: Product Manager
        Blacklist: Accounting Manager
        Other conditions: No healthcare positions
        Matches: no 
        
        -----
        
        Job title: "{job_title}"
        {job_title_filters}
        Matches: """

        # Remove the leading tabs from the multiline string
        template = textwrap.dedent(template)

        # Extract the whitelist and blacklist from the job filtering rules
        job_title_filters = Markdown.extract_content_from_markdown(self.job_filtering_rules, "Job Title Filters")
        # TODO: Raise an exception if the job title filters are not found

        prompt = PromptTemplate(input_variables=["job_title", "job_title_filters"], template=template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        output = chain.run(job_title=job_title, job_title_filters=job_title_filters)

        # Guard the output is one of the options
        if output.lower not in ['yes', 'no']:
            output = self._closest_matching_option(output, ['yes', 'no'])

        # Return the output as a boolean
        return output == 'yes'

    def job_description_passes_filters(self) -> bool:
        # Consider to add the resume to make a more informed decision, right now the responsibility to match resume against job description is on the recruiter.
        # This approach applies to what the user is interested in, not what the user is qualified for.

        template = """
        The task is to check if the job descriptions matches some requirements (whitelist and blacklist).

        ## Rules
        - Answer "yes" or "no"
        - Don't answer anything else
        - The matching is not exhaustive, the whitelist and blacklist are just examples
        - Answer "yes" if the job is related with the whitelist
        - Answer "no" if the job is related with the blacklist, the blacklist has priority over the whitelist
        - Answer "no" if something related to the blacklist is mentioned in the job description
        - Answer "no" if the job is not related with the whitelist or the blacklist

        ## Examples
        ### Example 1
        Job Description: Senior iOS Developer, with 5 years of experience in Swift and Objective-C, with strong passion for teaching and mentoring others
        Job Description Filters
        - Whitelist
         - Senior positions, Developer, Software Engineer
         - Teaching/communicating to others
        
        - Blacklist
         - Blockchain
         - Medical, I want nothing to do with healthcare

        Matches: yes
        
        ### Example 1
        Job Description: Senior iOS Developer for medical applications, with 5 years of experience in Swift and Objective-C, with strong passion for teaching and mentoring others
        Job Description Filters
        - Whitelist
         - Senior positions, Developer, Software Engineer
         - Teaching/communicating to others
        
        - Blacklist
         - Blockchain
         - Medical

        Matches: no

        -----

        Job Description:
        ``` 
        {job_description}
        ```
        
        Job Description Filters
        ```
        {job_description_filters}
        ```
        
        Matches: """

        # Remove the leading tabs from the multiline string
        template = textwrap.dedent(template)

        # Extract the whitelist and blacklist from the job filtering rules
        job_description_filters = Markdown.extract_content_from_markdown(self.job_filtering_rules, "Job Description Filters")
        # TODO: Raise an exception if the job title filters are not found

        prompt = PromptTemplate(input_variables=["job_description", "job_description_filters"], template=template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        output = chain.run(job_description=self.job_description_summary, job_description_filters=job_description_filters)

        # Guard the output is one of the options
        if output.lower not in ['yes', 'no']:
            output = self._closest_matching_option(output, ['yes', 'no'])

        # Return the output as a boolean
        return output == 'yes'

