![LinkedIn GPT - Automated job applications tailored to you.](img/github-banner.jpg)

## Disclaimer
I picked this up and working to fix it because I need a job :pray:

Okay. Job done! See my notes on how to make this fork work below:

### :pray:
Please :pray: :pray: read the [Setup](#Setup) section of this readMe before usage. T for Thanks

# LinkedIn GPT
Automatically apply to _LinkedIn Easy Apply_ jobs. This bot answers the application questions as well!

This is a fork of a fork of the original _LinkedIn Easy Apply Bot_, but it is a very special fork of a fork, this one relies on LLMs to answer the questions.

> This is for educational purposes only. I am not responsible if your LinkedIn account gets suspended or for anything else.

This bot is written in Python using Selenium and OpenAI.

## Fork Notes
The original bot implementation, couldn't handle open questions, just used keywords and predefined answers. Such couldn't complete a lot of the applications, as any open question or weird selector would make the bot unable to answer. Now that we have LLM, this is an easy problem to solve, just ask the bot to answer the question, and it will do it.

Another great benefit, is that you can provide way more information to the bot, so it can address truthfully the job requirements, and the questions, just as you would do. 

I did try to tidy the code a bit, but I didn't want to spend too much time on it, as I just wanted to get it working, so there is still a lot of work to do there.

Thank you for everyone that contributed to the original bot, and all the forks, made my work way easier.

_by Jorge Frías_

### Future updates
- I will keep updating this fork as I use it for my own "educational research".
- I will add features as I find fun applications, or I require them for my "educational research".

## Setup

### OpenAI API Key
First you need to provide your Open AI API key using environment variable `OPENAI_API_KEY`.

Create a `.env` file and set a variable like this:
`OPENAI_API_KEY = sk-xxxxx_key_from_openai_xxxxx`

> [You can set up the environment variable in your venv](https://stackoverflow.com/a/20918496/8150874)

I recommend to set a [Rate Limit](https://platform.openai.com/account/rate-limits) on your OpenAI account if you plan to leave the bot running for a long time, as it can get expensive quickly. I tried to use the cheapest models possible, but still requires `GPT-3.5-Turbo` to work.

### Your information
Before you read the below:
- Add your resume in PDF to the [`data_folder`](./data_folder) folder. File name should end with `Resume`, yes, you can include spaces.
- Add your cover letter in PDF to the `./data_folder` folder. File name should end with `cover_letter`, yes, it can be any name that includes the words `cover letter`.
- The above info already exists, but uneasy to locate. Buried in the middle of nowhere.

Your information is provided with a directory containing the following files:
- `config.yaml`. This file contains the information used to search on LinkedIn and fill in your personal information. Most of this is self-explanatory but if you need explanations please see the end of this `README`.
- `plain_text_resume.md`. Will be used to answer the questions, it's provided in MarkDown format.
- `plain_text_cover_letter.md`. Will be used when the form ask for a cover letter. When the form ask to write a cover letter (not upload it), the bot will adjust the cover letter to the job description.
  - You can use placeholders in your cover letter, a placeholder is defined as `[[placeholder]]`, the LLM will look onto the job description to fill in the placeholders. E.g. `[[company]]` will be replaced by the given company name.
- `personal_data.md`. More information about you, what you want of the job search, work authorization, extended information not covered by the resume, etc. This will be used to answer the questions, and inform other parts of the application. This file doesn't have any structure, will be interpreted by the LLM so fell free to add structure or information as you see fit.
- `job-filters.md`. This file gives you more control over the jobs that the bot applies to. There are two sections: `# Job Title Filters` and `# Job Description Filters` , these must be included on the document, these names are hardcoded on the script __do not modify them__.
- `resume.pdf`. Will be uploaded to LinkedIn when applying. The resume file can have a different name as long as it is a pdf file and the name contains the word `resume`. E.g. `Michael_Scott_Resume.pdf`.
- `cover_letter.pdf`. Will be uploaded to LinkedIn when applying if provided and the job application asks for it. The cover letter file can have a different name as long as it is a pdf file and the name contains the word `cover`. E.g. `Dwight_Schrute_Cover_Letter.pdf`.

  The `# Job Title Filters` section is used to filter the job title, and the `# Job Description Filters` section is used to filter the job description (once the job passes the job title filtering). The information on these sections is used on different steps of the process, you can have different rules on each section, or the same rules on both sections.
  
  Use natural language to explain what you are interested in, and what you are not. The LLM will try to understand what you mean, and will decide to apply or not to the job. 

> An `output` folder will be created, where you will find all generated answers to the questions.

The folder approach enables you to have multiple configurations (based on locations, roles...), and switch between them easily.

**You will find templates for all this files in the `templates` folder.**

### Install required libraries
> You should use a `virtual environment` for this, but it is not required.
```bash
pip3 install -r requirements.txt
```

## Execute
To run the bot, run the following in the command line, providing the path to your personal information directory as only argument.
```bash
python3 main.py path/to/your/personal/iformation/directory
```

## Config.yaml Explanations
Just fill in your email and password for linkedin.
```yaml
email: email@domain.com
password: yourpassword
```

This prevents your computer from going to sleep so the bot can keep running when you are not using it. Set this to True if you want this disabled.
```yaml
disableAntiLock: False
```

Set this to True if you want to look for remote jobs only.
```yaml
remote: False
```

This is for what level of jobs you want the search to contain. You must choose at least one.
```yaml
experienceLevel:
 internship: False
 entry: True
 associate: False
 mid-senior level: False
 director: False
 executive: False
```

This is for what type of job you are looking for. You must choose at least one.
```yaml
jobTypes:
 full-time: True
 contract: False
 part-time: False
 temporary: False
 internship: False
 other: False
 volunteer: False
```

How far back you want to search. You must choose only one.
```yaml
date:
 all time: True
 month: False
 week: False
 24 hours: False
 ```

A list of positions you want to apply for. You must include at least one.
```yaml
positions:
 #- First position
 #- A second position
 #- A third position
 #- ...
 ```

A list of locations you are applying to. You must include at least one.
```yaml
locations:
 #- First location
 #- A second location
 #- A third location
 #- ...
 - Remote
 ```

How far out of the location you want your search to go. You can only input 0, 5, 10, 25, 50, 100 miles.
```yaml
distance: 25
 ```

A list of companies to not apply to.
```yaml
companyBlacklist:
 #- company
 #- company2
 ```

A list of words that will be used to skip over jobs with any of these words in there.
```yaml
titleBlacklist:
 #- word1
 #- word2
 ```

Input your personal info. Include the state/province in the city name to not get the wrong city when choosing from a dropdown.
The phone country code needs to be exact for the one that is on linkedin.
The website is interchangeable for github/portfolio/website.
> This information should also be provided on `personal_data.md`.
```yaml
# ------------ Additional parameters: personal info ---------------
personalInfo:
 First Name: FirstName
 Last Name: LastName
 Phone Country Code: Canada (+1) # See linkedin for your country code, must be exact according to the international platform, i.e. Italy (+39) not Italia (+39)
 Mobile Phone Number: 1234567890
 Street address: 123 Fake Street
 City: Red Deer, Alberta # Include the state/province as well!
 State: YourState
 Zip: YourZip/Postal
 Linkedin: https://www.linkedin.com/in/my-linkedin-profile
 Website: https://www.my-website.com # github/website is interchangeable here
```

# Known issues with the parent of this fork
- The bot not always replaces correctly the placeholders on the cover letter.
- The bot sets 0 to all fields with int values. Terrible UX for fields about years of experience.This fork has handled this but set a fallback value of 4.
- If any field has problems with the answer, e.g. expected a number and the bot generated a text, the application will not proceed. [This fork now handles that case and lets the application proceed].
- Usually the first screen asking for contact information also ask for a `summary`, gpt doesn't fill this screen, so the application will not proceed. [This fork also now fills the summary but takes a while since it will communicate with OpenAI].
