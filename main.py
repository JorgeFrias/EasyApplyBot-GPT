import yaml
import argparse
from linkedineasyapply import LinkedinEasyApply
from validate_email import validate_email
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def init_browser():
    browser_options = Options()
    options = ['--disable-blink-features', '--no-sandbox', '--disable-extensions',
               '--ignore-certificate-errors', '--disable-blink-features=AutomationControlled','--disable-gpu','--remote-debugging-port=9222']
    for option in options:
        browser_options.add_argument(option)
    driver = webdriver.Chrome(ChromeDriverManager().install(),options=browser_options)
    return driver


def find_file(name_containing: str, with_extension: str, at_path: Path) -> Path:
    """
    Finds a file in a directory, given that the name contains a certain string and has a certain extension.
    :param name_containing: The string that the file name must contain. Case-insensitive.
    :param with_extension: The extension that the file must have, including the dot. Case-insensitive.
    :param at_path: The path to the directory where the file is.
    :return: The path to the first file that matches the criteria.
    """

    for file in at_path.iterdir():
        if name_containing.lower() in file.name.lower() and file.suffix.lower() == with_extension.lower():
            return file


def validate_data_folder(app_data_folder: Path):
    """
    Reads the data folder and validates that all the files are in place.

    Files:
    - config.yaml
    - resume.pdf
    - cover_letter.pdf
    - plain_text_resume.md
    - plain_text_cover_letter.md
    - personal_data.md

    :returns: config_file, resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file: The file paths, job_filters_file, output_folder: The output folder path in the app_data_folder.
    """

    config_file = Path(f"{app_data_folder}/config.yaml")
    plain_text_resume_file = Path(f"{app_data_folder}/plain_text_resume.md")
    plain_text_cover_letter_file = Path(f"{app_data_folder}/plain_text_cover_letter.md")
    personal_data_file = Path(f"{app_data_folder}/personal_data.md")
    job_filters_file = Path(f"{app_data_folder}/job_filters.md")

    # The resume and cover letter pdf can have more complex names as `JohnDoe-Resume.pdf` or `John-Doe-Cover-Letter.pdf`
    resume_file = find_file('resume', '.pdf', Path(app_data_folder))
    cover_letter_file = find_file('cover', '.pdf', Path(app_data_folder))

    print(config_file.exists())

    # Check all files exist
    # if not config_file.exists() or not resume_file.exists() or not cover_letter_file.exists() or not plain_text_resume_file.exists() or not plain_text_cover_letter_file.exists() or not personal_data_file.exists():
    #     raise Exception(f'Missing files in the data folder! You must provide:\n\t-config.yaml\n\t-resume.pdf\n\t-cover_letter.pdf\n\t-plain_text_resume.md\n\t-plain_text_cover_letter.md\n\t-personal_data.md\n\t-job_filters.md\n\nYou can find an example of these files in the example_data folder.')

    # Output folder
    output_folder = Path(f"{app_data_folder}/output")
    # Create the output folder if it doesn't exist
    if not output_folder.exists():
        output_folder.mkdir()

    # Return the file paths
    return config_file, resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file, job_filters_file, output_folder


def file_paths_to_dict(resume_file: Path, cover_letter_file: Path, plain_text_resume_file: Path, plain_text_cover_letter_file: Path, personal_data_file: Path, job_filters_file: Path) -> dict:
    parameters = {'resume': resume_file, 'coverLetter': cover_letter_file, 'plainTextResume': plain_text_resume_file, 'plainTextCoverLetter': plain_text_cover_letter_file, 'plainTextPersonalData': personal_data_file, 'jobFilters': job_filters_file}

    return parameters


def validate_yaml(config_yaml_path: Path):
    """
    Validates the yaml file, checking that all the mandatory parameters are present.
    :param config_yaml_path: The path to the yaml file.
    :return: The parameters extracted from the yaml file.
    """
    print('config yamal file', config_yaml_path)
    with open(config_yaml_path, 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc


    mandatory_params = ['email', 'password', 'disableAntiLock', 'remote', 'experienceLevel', 'jobTypes', 'date',
                        'positions', 'locations', 'distance', 'personalInfo']

    for mandatory_param in mandatory_params:
        if mandatory_param not in parameters:
            raise Exception(mandatory_param + ' is not inside the yml file!')

    assert validate_email(parameters['email'])
    assert len(str(parameters['password'])) > 0

    assert isinstance(parameters['disableAntiLock'], bool)

    assert isinstance(parameters['remote'], bool)

    assert len(parameters['experienceLevel']) > 0
    experience_level = parameters.get('experienceLevel', [])
    at_least_one_experience = False
    for key in experience_level.keys():
        if experience_level[key]:
            at_least_one_experience = True
    assert at_least_one_experience

    assert len(parameters['jobTypes']) > 0
    job_types = parameters.get('jobTypes', [])
    at_least_one_job_type = False
    for key in job_types.keys():
        if job_types[key]:
            at_least_one_job_type = True
    assert at_least_one_job_type

    assert len(parameters['date']) > 0
    date = parameters.get('date', [])
    at_least_one_date = False
    for key in date.keys():
        if date[key]:
            at_least_one_date = True
    assert at_least_one_date

    approved_distances = {0, 5, 10, 25, 50, 100, 10000000000000000}
    assert parameters['distance'] in approved_distances

    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0

    # assert len(parameters['uploads']) >= 1 and 'resume' in parameters['uploads']

    assert len(parameters['personalInfo'])
    personal_info = parameters.get('personalInfo', [])
    for info in personal_info:
        assert personal_info[info] != ''

    return parameters


def main(data_folder_path: Path):
    print(f"Using data folder path: {data_folder_path}")
    # Paths to the files inside the data folder
    config_file, resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file, job_filters_file, output_folder = validate_data_folder(data_folder_path)

    # Extract the parameters from the yaml file
    parameters = validate_yaml(config_file)
    # Add the remaining file paths to the parameters used by the bot
    parameters['uploads'] = file_paths_to_dict(resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file, job_filters_file)
    parameters['outputFileDirectory'] = output_folder

    # Start the bot
    browser = init_browser()
    bot = LinkedinEasyApply(parameters, browser)
    bot.login()
    bot.security_check()
    bot.start_applying()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process data folder path")
    parser.add_argument("data_folder", help="Path to the data folder")

    args = parser.parse_args()              # Parse the arguments
    data_folder = Path(args.data_folder)    # Convert to pathlib.Path object

    print(data_folder)

    # Tell the user if the data folder doesn't exist or is not a folder
    if not data_folder.exists():
        print(f"The data folder {data_folder} does not exist!")
        exit(1)
    if not data_folder.is_dir():
        print(f"The data folder {data_folder} is not a folder!")
        exit(1)

    main(args.data_folder)
