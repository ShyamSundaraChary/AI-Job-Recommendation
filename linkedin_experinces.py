from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re
import mysql.connector

# User-Agent List
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

# Updated Skills List (unchanged from your code)
skills_list = [
    "c", "c++", "java", "python", "javascript", "typescript", "c#", "php", "go", "rust", "swift", "kotlin", "ruby",
    "html", "css", "react", "react.js", "next.js", "angular", "vue.js", "svelte", "node.js", "express.js", "django", "flask",
    "spring boot", "laravel", "asp.net", "fast api", "ruby on rails", "jquery", "bootstrap", "tailwind css",
    "sql", "mysql", "postgresql", "mongodb", "firebase", "sqlite", "redis", "cassandra", "oracle db", "dynamodb",
    "machine learning", "deep learning", "data analysis", "data visualization", "tensorflow", "pytorch", "pandas",
    "numpy", "scikit-learn", "opencv", "natural language processing (nlp)", "keras", "xgboost", "matplotlib", "seaborn",
    "aws", "google cloud", "microsoft azure", "docker", "kubernetes", "jenkins", "terraform", "git", "ci/cd", "ci/cd pipelines",
    "ansible", "puppet", "chef", "cloudformation", "serverless", "lambda", "ec2", "s3", "gcp", "gcp bigquery", "azure",
    "ethical hacking", "penetration testing", "network security", "cryptography", "firewalls", "wireshark", "metasploit",
    "burp suite", "nmap", "owasp", "secure coding",
    "linux", "shell scripting", "windows server", "kernel development", "bash", "powershell", "unix", "Ubuntu",
    "git & github", "agile", "scrum", "design patterns", "software testing", "oop", "system design", "microservices",
    "rest", "rest apis", "restful apis", "graphql", "websockets", "soap", "grpc", "api gateway",
    "unit testing", "integration testing", "selenium", "pytest", "junit", "test automation", "mocking",
    "big data", "hadoop", "spark", "kafka", "flink", "hive", "pig", "data warehousing", "database fundamentals",
    "blockchain", "solidity", "ethereum", "smart contracts", "web3",
    "game development", "unity", "unreal engine", "opengl", "directx",
    "android development", "ios development", "flutter", "react native", "xamarin",
    "embedded systems", "iot", "arduino", "raspberry pi", "rtos",
    "devops", "sre", "sre (site reliability engineering)", "monitoring", "prometheus", "grafana", "logging", "splunk",
    "computer vision", "reinforcement learning", "statistics", "probability", "linear algebra",
    "langchain", "beautiful soup", "scrapy", "asyncio", "multithreading", "concurrent programming", "sqlalchemy",
    "jira", "trello", "confluence", "bitbucket", "gitlab", "github", "svn"
]

# Database Connection
def connect_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="shyam",
            password="shyam",
            database="jobs_experienced"  # New database for experienced candidates
        )
    except mysql.connector.Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        raise

# Create Job Table
def create_table(conn, job_title):
    cursor = conn.cursor()
    table_name = job_title.replace(" ", "_").lower()
    query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_title VARCHAR(100) NOT NULL,
            company VARCHAR(100) NOT NULL,
            location VARCHAR(100),
            salary VARCHAR(100),
            skills_required TEXT NOT NULL,
            job_link VARCHAR(500),
            posted_date DATE,
            applicants INT,
            source VARCHAR(20) DEFAULT 'LinkedIn',
            experience_level VARCHAR(50),
            UNIQUE (job_title, company, source)
        )
    """
    try:
        cursor.execute(query)
        conn.commit()
    except mysql.connector.Error as e:
        print(f"[ERROR] Failed to create table for {job_title}: {e}")
    finally:
        cursor.close()

# Insert Jobs into DB
def insert_jobs(conn, job_title, jobs_data):
    if not jobs_data:
        print(f"[WARNING] No jobs to insert for {job_title}")
        return
    cursor = conn.cursor()
    table_name = job_title.replace(" ", "_").lower()
    query = f"""
        INSERT IGNORE INTO {table_name} 
        (job_title, company, location, salary, skills_required, job_link, posted_date, applicants, source, experience_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        print(f"[DEBUG] Attempting to insert {len(jobs_data)} jobs for {job_title}")
        cursor.executemany(query, [
            (
                job["job_title"][:100],
                job["company"][:100],
                job["location"][:100],
                job["salary"],
                job["skills_required"],
                job["job_link"],
                job["posted_date"],
                job["applicants"],
                "LinkedIn",
                job["experience_level"]
            ) for job in jobs_data
        ])
        conn.commit()
        print(f"[INFO] Inserted {cursor.rowcount} jobs for {job_title}")
    except mysql.connector.Error as e:
        print(f"[ERROR] Failed to insert jobs for {job_title}: {e}")
    finally:
        cursor.close()

# Parse Posted Date
def parse_posted_date(posted_text):
    try:
        posted_text = posted_text.lower()
        today = datetime.now().date()
        if "hour" in posted_text or "minute" in posted_text or "just now" in posted_text:
            return today
        elif "day" in posted_text:
            days = int(re.search(r'\d+', posted_text).group())
            return today - timedelta(days=days)
        elif "week" in posted_text:
            weeks = int(re.search(r'\d+', posted_text).group())
            return today - timedelta(days=weeks * 7)
        else:
            return today
    except:
        return datetime.now().date()

# Scrape Individual Job Page
def scrape_job_page(job_url, driver):
    try:
        driver.get(job_url)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "top-card-layout"))
            )
        except:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        time.sleep(random.uniform(3, 5))

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 3))

        soup = BeautifulSoup(driver.page_source, "lxml")

        # Extract Title
        title = soup.find("h1", class_="top-card-layout__title")
        if not title:
            title = soup.find("h1")
        title = title.text.strip() if title else "Not Available"

        # Extract Company
        company_tag = soup.find("a", class_="topcard__org-name-link")
        if not company_tag:
            company_tag = soup.find("span", class_="topcard__flavor")
        company = company_tag.text.strip() if company_tag else "Not Available"

        # Extract Location
        location_tag = soup.find("span", class_="topcard__flavor--bullet")
        location = location_tag.text.strip() if location_tag else "Not Available"

        # Filter by Location (India)
        if "India" not in location:
            print(f"[INFO] Skipping {job_url}: Location ({location}) not in India")
            return None

        # Extract Posted Time
        metadata = soup.find("span", class_="posted-time-ago__text")
        posted_time = metadata.text.strip() if metadata else "Not Available"
        posted_date = parse_posted_date(posted_time)

        # Filter by Posted Time (within 1 month)
        today = datetime.now().date()
        if (today - posted_date).days > 30:
            print(f"[INFO] Skipping {job_url}: Posted date ({posted_date}) older than 1 month")
            return None

        # Extract Applicants
        applicants = 0
        applicants_tag = soup.find("span", class_="num-applicants__caption")
        if applicants_tag:
            applicants_text = applicants_tag.text.strip()
            match = re.search(r'\d+', applicants_text)
            if match:
                applicants = int(match.group())
        else:
            applicants_text = soup.find(string=re.compile(r'\d+\s*(applicants|applied)', re.I))
            if applicants_text:
                match = re.search(r'\d+', applicants_text)
                if match:
                    applicants = int(match.group())
            else:
                stats_container = soup.find("div", class_=re.compile("stats|applicants", re.I))
                if stats_container:
                    applicant_stat = stats_container.find(string=re.compile(r'\d+\s*(applicants|applied)', re.I))
                    if applicant_stat:
                        match = re.search(r'\d+', applicant_stat)
                        if match:
                            applicants = int(match.group())

        # Extract Salary
        salary = "Not disclosed"

        # Extract Job Description and Match Skills
        description = soup.find("div", class_="show-more-less-html__markup")
        description_text = description.text.strip() if description else ""
        matched_skills = []
        for skill in skills_list:
            if re.search(rf'\b{re.escape(skill)}\b', description_text, re.IGNORECASE):
                matched_skills.append(skill)
        skills = ", ".join(matched_skills) if matched_skills else "Not Available"

        experience_tag = soup.find("span", class_="description__job-criteria-text")
        experience_level = experience_tag.text.strip() if experience_tag else "Not Available"

        job_data = {
            "job_title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "skills_required": skills,
            "job_link": job_url,
            "posted_date": posted_date.strftime("%Y-%m-%d"),
            "applicants": applicants,
            "source": "LinkedIn",
            "experience_level": experience_level
        }

        return job_data
    except Exception as e:
        print(f"[ERROR] Failed to scrape {job_url}: {e}")
        return None

# Scrape Job Listings and Insert into DB
def scrape_linkedin_jobs(job_titles, driver_path, jobs_per_title=25):
    # Setup WebDriver
    service = Service(driver_path)
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-webgl")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Connect to Database
    conn = connect_db()

    # Create tables for each job title
    for job_title in job_titles:
        create_table(conn, job_title)

    all_jobs_data = []
    jobs_collected_per_title = {title: 0 for title in job_titles}

    try:
        for job_title in job_titles:
            print(f"\n[INFO] Scraping jobs for: {job_title}")
            # Use LinkedIn filter for Mid-Senior level (f_E=3,4 for Mid-Senior and Senior)
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={job_title.replace('_', '%20')}&location=India&f_E=3%2C4"
            driver.get(search_url)
            
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__results-list"))
                )
            except Exception as e:
                print(f"[ERROR] Failed to load search results for {job_title}: {e}")
                continue

            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 3))

            soup = BeautifulSoup(driver.page_source, "lxml")
            job_cards = soup.find_all("div", class_="base-card")

            job_urls = []
            for card in job_cards:
                link = card.find("a", class_="base-card__full-link")
                if link and link.get("href"):
                    job_urls.append(link["href"])
                if len(job_urls) >= jobs_per_title * 2:
                    break

            print(f"[INFO] Found {len(job_urls)} job URLs for {job_title}")

            title_jobs_data = []
            for job_url in job_urls:
                if jobs_collected_per_title[job_title] >= jobs_per_title:
                    break
                job_data = scrape_job_page(job_url, driver)
                if job_data:
                    title_jobs_data.append(job_data)
                    jobs_collected_per_title[job_title] += 1
                    all_jobs_data.append(job_data)
                    print("\nJob Data (Schema Format):")
                    print(f"job_title: {job_data['job_title']}")
                    print(f"company: {job_data['company']}")
                    print(f"location: {job_data['location']}")
                    print(f"salary: {job_data['salary']}")
                    print(f"skills_required: {job_data['skills_required']}")
                    print(f"job_link: {job_data['job_link']}")
                    print(f"posted_date: {job_data['posted_date']}")
                    print(f"applicants: {job_data['applicants']}")
                    print(f"source: {job_data['source']}")
                    print(f"experience_level: {job_data['experience_level']}")
                    print("-" * 50)

                time.sleep(random.uniform(3, 5))

            # Insert jobs for this title into the database
            insert_jobs(conn, job_title, title_jobs_data)

    except Exception as e:
        print(f"[ERROR] General error during scraping: {e}")
    finally:
        driver.quit()
        conn.close()

    print(f"\n[INFO] Total jobs scraped: {len(all_jobs_data)}")
    return all_jobs_data

# Main Execution with Timing
if __name__ == "__main__":
    start_time = time.time()

    driver_path = "C:/Users/shyam/OneDrive/Desktop/job-portal-app/chromedriver-win64/chromedriver.exe"
    job_titles = ["devops_engineer", "full_stack_developer", "java_developer", "python_developer", "software_engineer"]
    jobs_per_title = 25
    scrape_linkedin_jobs(job_titles, driver_path, jobs_per_title)

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"\n[INFO] Total execution time: {execution_time:.2f} seconds")