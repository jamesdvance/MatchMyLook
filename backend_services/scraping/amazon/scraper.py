
import boto3
import pandas as pd
import selenium
import sys
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options	
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException, TimeoutException

"""
class AmazonScraper():

self.signin_page = "https://www.amazon.com/gp/sign-in.html"

	def __init__(self, search_query):
		self.qry = search_query
"""
def get_login_info(pw_path):
# "C:/Users/J/AWS/passwords.csv"
	login_csv = pd.read_csv(pw_path)
	return login_csv['email'].item(), login_csv['pwd'].item()

def start_browser(exe_path):
	#'C:/Users/J/geckodriver-v0.24.0-win64/geckodriver.exe'
	#options = Options()
	#, options=options)
	#options.headless=False
	return webdriver.Chrome(executable_path=exe_path)

def login_amzn(browser, email, pw):
	browser.get("https://www.amazon.com/gp/sign-in.html")
	email_input = browser.find_element_by_id('ap_email')
	pw_input = browser.find_element_by_id('ap_password')
	email_input.send_keys(email)
	pw_input.send_keys(pw)
	browser.find_element_by_id('signInSubmit').click()
	return browser

def search_amzn(browser, search_query):
	searchfield = browser.find_element_by_id('twotabsearchtextbox')
	searchfield.send_keys(search_query)
	search_btn = browser.find_element_by_xpath('/html/body/div[1]/header/div/div[1]/div[3]/div/form/div[2]/div/input').click()
	return browser 

def handle_modal(browser):
	top_list_path = '//*[@id="amzn-ss-text-image-link"]'
	print("caught modal exception ")
	element = browser.find_element_by_id('p2dPopoverID-no-button-announce')
	actions = ActionChains(browser)
	actions.move_to_element(element)
	actions.click(element)
	actions.perform()
	browser.implicitly_wait(5)
	return browser

def scrape_single_product(browser, i):
	"""
	Browser should be on search results when it starts 
	n should be the nth product on the page
	"""
	top_list_path = '//*[@id="amzn-ss-text-image-link"]'
	price_id_1 = 'price_inside_buybox'
	price_id_2 = 'priceblock_ourprice'
	pg_dict = {}
	# Wait for page to load
	try:
		browser.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-index='{0}'] a[class='a-link-normal a-text-normal']".format(str(i)))))
	# Timeout exception
	except TimeoutException: 
		return browser, pd.DataFrame(), False # if link not found, skip
	# Looking for name first
	try:
		pg_dict['title'] = browser.find_element(By.CSS_SELECTOR, "div[data-index='{0}'] span[class='a-size-base-plus a-color-base a-text-normal']".format(str(i))).text
	except NoSuchElementException:
		pass
	# Looking for price on front page
	try:
		int_price = browser.find_element(By.CSS_SELECTOR, "div[data-index='{0}'] span[class='a-price'] span[class='a-price-whole']".format(str(i))).text
		dec_price = browser.find_element(By.CSS_SELECTOR, "div[data-index='{0}'] span[class='a-price'] span[class='a-price-fraction']".format(str(i))).text
		pg_dict['price'] = Decimal(int_price+"."+dec_price)
	except NoSuchElementException:
		pass
	# Clicking Into Product Page
	link = browser.find_element(By.CSS_SELECTOR, "div[data-index='{0}'] a[class='a-link-normal a-text-normal']".format(str(i))).get_attribute("href")
	
	# Get ASIN from upper div
	pg_dict['asin'] =  browser.find_element(By.CSS_SELECTOR, "div[data-index='{0}']".format(str(i))).get_attribute('data-asin')
	# Try and parse ASIN from link text
	"""
	post_dp = link[link.find('dp/')+3:len(link)]
	if post_dp != link[2:len(link)]: # if they are the same 'dp/' could not be found
		pg_dict['asin'] = post_dp[0:post_dp.find("/")].strip()
	else:
		pass
	"""
	# Click into product page
	browser.get(link)
	#Clicking Associate Stripe Drop-Down
	try:
		browser.wait.until(EC.element_to_be_clickable((By.XPATH, top_list_path)))
	except TimeoutException:
			return browser, pd.DataFrame(), True
	try:
		afil_link = browser.find_element_by_xpath(top_list_path).click()
	except ElementClickInterceptedException:
		browser = handle_modal(browser)
		afil_link = browser.find_element_by_xpath(top_list_path).click()

	element = browser.wait.until(EC.presence_of_element_located((By.ID, 'amzn-ss-image-textarea')))		
	link_html = browser.find_element_by_id('amzn-ss-text-image-textarea').text
	j = 0 
	while not(link_html):
	# go back
		try:
			afil_link = browser.find_element_by_xpath(top_list_path).click()
		except ElementClickInterceptedException:
			browser = handle_modal(browser)
			afil_link = browser.find_element_by_xpath(top_list_path).click()
			link_html = browser.find_element_by_id('amzn-ss-text-image-textarea').text
		if link_html:
			break
		browser.implicitly_wait(5)
		j+=1
		if j >10:
			# will go back in seperate function
			return browser, pd.DataFrame(), True
	pg_dict['affil_link'] = [link_html]
	# Stars
	try:
		stars_txt = browser.find_element_by_id('acrPopover').get_attribute('title')# or title
		pg_dict['stars'] = [Decimal(stars_txt.replace("out of 5 stars", "").strip())]
	except NoSuchElementException:
		pg_dict['stars'] = 0.0
	# Price - need to get price from front page. 
	# Could go look up ASIN from amazon affiliate section
	if not('price' in pg_dict):
		try:
			try:
				price_txt = browser.find_element_by_id(price_id_1).text
				pg_dict['price'] = [Decimal(price_txt.replace("$","").strip())]
			except NoSuchElementException:
				try:
					price_txt = browser.find_element_by_id(price_id_2).text
					pg_dict['price'] = [Decimal(price_txt.replace("$","").strip())]
				except NoSuchElementException:
					pg_dict['price'] = None
		except:
			return browser, pd.DataFrame(), True
	# ASIN
	if not('asin' in pg_dict):
		try:
			pg_dict['asin'] = [browser.find_element_by_css_selector("table[id='productDetails_detailBullets_sections1'] tr:nth-of-type(5) td").text]
		except NoSuchElementException:
			pg_dict['asin'] = 'None'
	# Name
	if not('title' in pg_dict):
		try:
			pg_dict['title'] = [browser.find_element_by_id("productTitle").text]
		except NoSuchElementException:
			pg_dict['title'] = "couldn't find the title"
	item_df = pd.DataFrame(pg_dict)
	return browser, item_df, True

def scrape_products_page(browser):
	page_df = pd.DataFrame()

	# data-cell-widget
	# Wrap in a try/accept. If not found error, don't want. 
	browser.wait = WebDriverWait(browser, 45)
	try:
		browser.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"div[class='s-result-list s-search-results sg-row'] a[class='a-link-normal a-text-normal']" )))
	except TimeoutException:
		browser.implicitly_wait(10)
	divs = browser.find_elements_by_css_selector("div[class='s-result-list s-search-results sg-row'] a[class='a-link-normal a-text-normal']")
	items = len(divs)
	for i in range(items):
		browser, item_df, back = scrape_single_product(browser, i)
		page_df = page_df.append(item_df)
		if back:
			browser.execute_script("window.history.go(-1)")
	return browser, page_df

def next_page(browser):
	this_page_btn = browser.find_element(By.CSS_SELECTOR, "ul[class='a-pagination'] li[class='a-selected']")
	next_page_btn = browser.execute_script('return arguments[0].nextElementSibling', this_page_btn)
	next_page_btn.click()
	return browser

# This would be the lambda function
def scrape_all(exe_path, search_qry, am_email, am_pw, n_pages):

	browser = start_browser(exe_path)
	browser = login_amzn(browser, am_email, am_pw)
	browser = search_amzn(browser, search_qry)

	browser, final_df = scrape_products_page(browser)
	# Scrape Nth pages
	for i in range(n_pages):
		browser = next_page(browser)
		browser, new_df = scrape_products_page(browser)
		final_df = final_df.append(new_df)
	return final_df

if __name__ =='__main__':
	email, pw = get_login_info( "C:/Users/J/AWS/passwords.csv")
	# "C:/Users/J/geckodriver-v0.24.0-win64/geckodriver.exe"
	qry_term = sys.argv[1]
	res_df = scrape_all(exe_path="C:/Users/J/chromedriver/chromedriver.exe", search_qry=qry_term+" gifts", am_email=email, am_pw=pw, n_pages=3)
	keep_df = res_df[(pd.notnull(res_df['affil_link']))&(pd.notnull(res_df['asin']))&(res_df['asin']!='None')&(res_df['asin']!='')&(res_df['stars']>0)&(pd.notnull(res_df['stars']))&(res_df['price']>0)&(pd.notnull(res_df['price']))]
	keep_df = keep_df.reset_index(drop=True)
	keep_df.to_csv("C:/Users/J/Desktop/scraped_gifts/scraped_amzn_gifts_"+qry_term+".csv", index=False)



