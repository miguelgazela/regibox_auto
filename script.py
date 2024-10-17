from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta, timezone
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import re
import pytz
import os

local_tz = pytz.timezone("Europe/Lisbon")

email = os.getenv('EMAIL')
password = os.getenv('PASSWORD')

print("Script script!")

# Function to extract the timestamp from the div's ID
def extract_timestamp(time_slot_id):
    # Use regex to find the timestamp (assuming the timestamp is numeric and appears after 'feed_time_slot')
    match = re.search(r'feed_time_slot(\d+)', time_slot_id)
    if match:
        return int(match.group(1))  # Return the timestamp as an integer
    return None  # In case no match is found

def get_next_available_day(days_ahead):
    today = datetime.now()
    next_day = today + timedelta(days=days_ahead)

    year = next_day.year
    month = next_day.month - 1 # zero based month, for some reason
    day = next_day.day

    return f"{year}-{month}-{day}"

def convert_to_local_time(timestamp):
    utc_time = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    local_time = utc_time.astimezone(local_tz)
    return local_time.strftime("%H:%M"), local_time.weekday()

# Function to check if the slot's time is within the allowed slots for today
def is_valid_slot_for_day(weekday, slot_time):
    # Define the allowed times for each day
    valid_times = {
        0: ['17:00', '18:00'],  # Monday
        1: ['18:00', '19:00'],  # Tuesday
        2: ['17:00', '18:00'],  # Wednesday
        3: [],                  # Thursday
        4: ['17:00', '18:00'],  # Friday
        5: ['10:30', '11:40'],  # Saturday
        6: []                   # Sunday
    }
    
    # Check if today is a valid class day
    if weekday not in valid_times or len(valid_times[weekday]) == 0:
        return False
    
    # Check if the slot time is in the list of valid times for the day
    return slot_time in valid_times[weekday]

def click_enroll_button(slot_element):
    try:
        enroll_button = slot_element.find_element(By.XPATH, ".//button[text()='INSCREVER']")
        driver.execute_script("arguments[0].click();", enroll_button)
        print("Clicked 'INSCREVER' button!")
    except Exception as e:
        print(f"No 'INSCREVER' button found or could not click: {str(e)}")

# This script will book the class on the next available day, which on regibox is 3 days ahead.
# So, on Monday we can book the Thursday class. 
# We can skip thursdays, since there's no classes on Sunday, and mondays since thursdays are recovery days

days_to_skip = [0, 3] # 0 = Monday, 3 = Thursday

current_weekday = datetime.now().weekday()

# check if the current day is in the skip list
if current_weekday in days_to_skip and False:
    print("Script won't run today because it's a day to skip.")
else:
    print("Running script as it's an allowed day.")

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--no-sandbox")  # Necessary for running in some environments
    chrome_options.add_argument("--disable-dev-shm-usage")  # To avoid resource limits in some environments
    chrome_options.add_argument("--window-size=1920x1080")  # Set window size for better rendering of elements
    # Optionally, you can add more options for debugging
    # chrome_options.add_argument("--remote-debugging-port=9222")

    # Set up WebDriver (e.g., Chrome)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Open the booking site
    driver.get('https://www.regibox.pt/app/app_nova/login.php?id_box=360&lang=&type=')

    # Wait for the login form to appear
    try:
        username_field = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "login"))
        )

        print("Login visible")

        # Now that the login form is visible, fill out the form
        username_field.send_keys(email)  # Enter username
        driver.find_element(By.ID, 'password').send_keys(password)  # Enter password
        driver.find_element(By.ID, 'but_dados').click()

        # Wait until the next page (e.g., bottom bar) loads
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, 'bot_bar'))
        )

        print("Login successful!")

        driver.execute_script('open_page("calendario_aulas","&source=mes");')

        # Wait until the calendar is visible

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'calendar'))
        )
        print('Calendar is visible')

        # 3 days ahead because that's the limit on Regibox
        next_day_date = get_next_available_day(1)
        print(next_day_date)

        next_day_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//div[contains(@data-date, '{next_day_date}')]"))
        )
        #print(next_day_element.get_attribute('outerHTML'))

        driver.execute_script("arguments[0].click();", next_day_element)

        time_slots = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[starts-with(@id, 'feed_time_slot')]"))
        )
        
        if time_slots:
            for slot in time_slots:
                slot_id = slot.get_attribute('id')
                timestamp = extract_timestamp(slot_id)
                                
                if timestamp:
                    readable_time, weekday = convert_to_local_time(timestamp)
                    print(f"Class starts at: {readable_time} (Weekday: {weekday})")
                    
                    if is_valid_slot_for_day(weekday, readable_time):
                        print("valid slot!")
                        click_enroll_button(slot)
        else:
            print("No time slots found")

    except Exception as e:
        print("Error: ", e)

    finally:
        driver.quit()