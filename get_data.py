"""
Downloads the civil remedy notice filings for the specified years from the Florida Department of Financial Services
"""


import time
from datetime import datetime
import calendar
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import pandas as pd
import os
import platform

from tqdm import tqdm

##### PARAMETERS #####
start_year = 2015
end_year = 2023
target_dir = "working_data"
######################

civil_remedy_url = "https://apps.fldfs.com/CivilRemedy/SearchFiling.aspx"


def get_download_path():
    """Returns the default downloads path for linux or windows"""
    if platform.system() == 'Linux' or platform.system() == 'Darwin':
        return os.path.join(os.path.expanduser('~'), 'Downloads')
    elif platform.system() == 'Windows':
        return os.path.join(os.path.expanduser('~'), 'Downloads')
    else:
        raise Exception('Unsupported Operating System')


# Function to wait if a download is in process
def is_downloading_process_completed(download_dir, timeout=300):
    time.sleep(1)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if any(fname.endswith(".part") for fname in os.listdir(download_dir)):
            time.sleep(1)
        else:
            return True  # download is complete
    return False  # download timed out

# Function to wait for the download to complete
def is_downloaded_file_ready(download_dir, file_name, timeout=5):
    start_time = time.time()
    file_path = os.path.join(download_dir, file_name)

    while time.time() - start_time < timeout:
        if os.path.exists(file_path):
            return True
        time.sleep(1)
    return False


def downloader(driver, start_date, end_date, file_name, download_dir, target_dir):
    success = False
    driver.implicitly_wait(5)

    # Find the submission date fields and fill them in
    start_date_field = driver.find_element(By.ID, "ctl00_phPageContent_txtSubmissionStartDate")
    start_date_field.clear()
    start_date_field.send_keys(start_date)
    end_date_field = driver.find_element(By.ID, "ctl00_phPageContent_txtSubmissionEndDate")
    end_date_field.clear()
    end_date_field.send_keys(end_date)

    # Press search button
    driver.find_element(By.ID, "ctl00_phPageContent_btnSearch").click()

    # Wait for the results to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ctl00_phPageContent_lnkExportResultsTop"))
    )

    # press export results button
    driver.find_element(By.ID, "ctl00_phPageContent_lnkExportResultsTop").click()

    raw_downloaded_file_name = "FilingSearch.csv"

    try:
        # Wait to see if "too large to export" text appears
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'too large to export')]")))
    except TimeoutException:
        # "too large to export" text did not appear
        # Wait for the downloading process to finish
        if is_downloading_process_completed(download_dir):
            # Wait for the file to be ready
            if is_downloaded_file_ready(download_dir, raw_downloaded_file_name):
                # rename the file
                new_file_path = os.path.join(download_dir, f"{file_name}.csv")
                os.rename(os.path.join(download_dir, raw_downloaded_file_name), new_file_path)
                shutil.move(new_file_path, os.path.join(f"./{target_dir}/", f"{file_name}.csv"))
                success = True

    # Press edit search button
    driver.find_element(By.ID, "ctl00_phPageContent_btnEditSearchTop").click()
    time.sleep(1)
    return success

def date_range_downloader(driver, date_range, download_dir, missing_files, target_dir):
    print(f">> Downloading {date_range[2]}...", end=" ")
    status = downloader(driver, date_range[0], date_range[1], f"res-{date_range[2]}", download_dir, target_dir)
    if not status:
        missing_files.append(date_range)
        print("Failed!")
    else:
        print("Done.")


def date_range_generator(start_year, end_year, period_length: str):
    """
    This function generates a list of tuples with the start and end dates of each period.
    :param start_year: Start year for the date range
    :param end_year: End year for the date range
    :param period_length: "day", "3-day", "week", "half_month", "month", "quarter"
    :return: a list of tuples with the start and end dates of each period and the title for that period
    """
    periods = []
    if period_length == "day":
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                last_day = calendar.monthrange(year, month)[1]
                for day in range(1, last_day + 1):
                    periods.append([f"{month}/{day}/{year}", f"{month}/{day}/{year}", f"{year}-{month}-{day}"])
    elif period_length == "3-day":
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                last_day = calendar.monthrange(year, month)[1]
                for day in range(0, 9):
                    start_date = datetime(year, month, day * 3 + 1).strftime("%m/%d/%Y")
                    end_date = datetime(year, month, day * 3 + 3).strftime("%m/%d/%Y")
                    periods.append([start_date, end_date, f"{year}-{month}-3D{day}"])
                start_date = datetime(year, month, 28).strftime("%m/%d/%Y")
                end_date = datetime(year, month, last_day).strftime("%m/%d/%Y")
                periods.append([start_date, end_date, f"{year}-{month}-3D{10}"])
    elif period_length == "week":
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                last_day = calendar.monthrange(year, month)[1]
                for week in range(0, 3):
                    start_date = datetime(year, month, week * 7 + 1).strftime("%m/%d/%Y")
                    end_date = datetime(year, month, week * 7 + 7).strftime("%m/%d/%Y")
                    periods.append([start_date, end_date, f"{year}-{month}-W{week + 1}"])
                start_date = datetime(year, month, 22).strftime("%m/%d/%Y")
                end_date = datetime(year, month, last_day).strftime("%m/%d/%Y")
                periods.append([start_date, end_date, f"{year}-{month}-W{4}"])
    elif period_length == "half_month":
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                start_date = datetime(year, month, 1).strftime("%m/%d/%Y")
                end_date = datetime(year, month, 15).strftime("%m/%d/%Y")
                periods.append([start_date, end_date, f"{year}-{month}-H1"])
                start_date = datetime(year, month, 16).strftime("%m/%d/%Y")
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).strftime("%m/%d/%Y")
                periods.append([start_date, end_date, f"{year}-{month}-H2"])
    elif period_length == "month":
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                start_date = datetime(year, month, 1).strftime("%m/%d/%Y")
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).strftime("%m/%d/%Y")
                periods.append([start_date, end_date, f"{year}-{month}"])
    elif period_length == "quarter":
        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                start_date = datetime(year, quarter * 3 - 2, 1).strftime("%m/%d/%Y")
                end_date = datetime(year, quarter * 3, calendar.monthrange(year, quarter * 3)[1]).strftime("%m/%d/%Y")
                periods.append([start_date, end_date, f"{year}-Q{quarter}"])
    elif period_length == "year":
        for year in range(start_year, end_year + 1):
            start_date = datetime(year, 1, 1).strftime("%m/%d/%Y")
            end_date = datetime(year, 12, 31).strftime("%m/%d/%Y")
            periods.append([start_date, end_date, f"{year}"])

    else:
        raise Exception("Invalid period length")
    return periods


# Use this function to get the download path
download_dir = get_download_path()

# Check if a file with any name but ending ".par" exists in the download directory
if any(fname.endswith(".part") for fname in os.listdir(download_dir)):
    print("There is a file with extension .part in the download directory. Please remove it and try again.")
    exit(1)

# Check an old downloaded file is still in the download directory
if any(fname.startswith("FilingSearch") for fname in os.listdir(download_dir)):
    print("There is an old downloaded file in the download directory. Please remove it and try again.")
    exit(1)

options = webdriver.FirefoxOptions()
# options.headless = True

# Initialize the WebDriver
driver = webdriver.Firefox(options=options)

# Open the webpage
driver.get(civil_remedy_url)

# Loop through each month
missing_files = []
date_ranges = date_range_generator(start_year, end_year, "month")
for date_range in date_ranges:
    date_range_downloader(driver, date_range, download_dir, missing_files, target_dir)

# Trying shorter date ranges for failed downloads
for date_range_type in ["week", "3-day", "day"]:
    if len(missing_files) > 0:
        print(f"\n>>>>> Trying again to download missing files - period length: {date_range_type}")

        missed_date_ranges = pd.DataFrame(missing_files, columns=["start_date", "end_date", "title"])
        missed_date_ranges.start_date = pd.to_datetime(missed_date_ranges.start_date)
        missed_date_ranges.end_date = pd.to_datetime(missed_date_ranges.end_date)

        missing_files = []
        date_ranges = date_range_generator(start_year, end_year, date_range_type)
        for date_range in date_ranges:
            # check if the date range is in the missing files dataframe
            if len(missed_date_ranges[(missed_date_ranges.start_date <= pd.to_datetime(date_range[0])) &
                                      (missed_date_ranges.end_date >= pd.to_datetime(date_range[1]))]) > 0:
                date_range_downloader(driver, date_range, download_dir, missing_files, target_dir)
    else:
        break

driver.quit()

if len(missing_files) > 0:
    print("\n >> Failed to download the following files:")
    missing_files = pd.DataFrame(missing_files, columns=["start_date", "end_date", "title"])
    print(missing_files)
    missing_files.to_csv(".\working_data\missing_files.csv", index=False)
else:
    print("\n >> All files downloaded successfully")


# organize downloaded data
df = pd.DataFrame()
files_list = os.listdir("./working_data/downloaded_data")
for file in tqdm(files_list):
    if file.endswith(".csv"):
        df_temp = pd.read_csv("./working_data/downloaded_data/" + file)
        df = pd.concat([df, df_temp], ignore_index=True)

df["Submission Date"] = pd.to_datetime(df["Submission Date"])
df["Year"] = df["Submission Date"].dt.year
for year in range(df.Year.min(), df.Year.max() + 1):
    df[df["Year"] == year].to_csv("./working_data/civil-remedy-notice-filings-" + str(year) + ".csv", index=False)

# df.to_csv(f"./working_data/civil-remedy-notice-filings-{df.Year.min()}-{df.Year.max()}.csv", index=False)