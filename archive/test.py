from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

# Set up the Chrome driver
driver = webdriver.Chrome()  # or specify the path like webdriver.Chrome(executable_path='path/to/chromedriver')

# Open a web page
driver.get('http://www.google.com')

# Wait for the page to load
time.sleep(2)

# Click on the URL bar and clear it
url_bar = driver.find_element_by_xpath('//input[@title="Search"]')
url_bar.click()
url_bar.clear()

# Enter the search text and submit
search_text = "OpenAI ChatGPT"
url_bar.send_keys(search_text)
url_bar.send_keys(Keys.RETURN)

# Wait for the results to load
time.sleep(5)

# Close the browser
driver.quit()
