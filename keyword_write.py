import os
import requests
import urllib.parse
import csv
import re
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# .env 파일에서 인증 정보 로드
load_dotenv()
CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 검색할 키워드 리스트
keywords = ["떡볶이", "김밥", "라면"]

# 네이버 API 헤더 설정
headers = {
    "X-Naver-Client-Id": CLIENT_ID,
    "X-Naver-Client-Secret": CLIENT_SECRET
}

# 저장 경로 및 파일명 설정
save_dir = "c:/python_project"
os.makedirs(save_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"naver_blog_results_{timestamp}.csv"
save_path = os.path.join(save_dir, filename)

# 크롬 드라이버 설정
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 감성 키워드
sentiment_keywords = ["맛있", "추천", "좋았", "별로", "다신", "최고", "최악", "행복"]

# 본문 정제 함수 with 다중 셀렉터
def extract_blog_content(link):
    try:
        driver.get(link)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe"))
        )
        driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, "iframe"))
        soup = BeautifulSoup(driver.page_source, "html.parser")

        selectors = [
            "div.se-main-container",
            "div#postViewArea",
            "div#contentArea",
            "div.post-view",
            "section.blog"
        ]
        content = None
        for sel in selectors:
            content = soup.select_one(sel)
            if content:
                break

        if not content:
            return "(본문 없음)"

        text = content.get_text(separator="\n", strip=True)
        lines = text.split("\n")

        keyword_lines = [line for line in lines if any(k in line for k in keywords)]
        sentiment_lines = [line for line in lines if any(k in line for k in sentiment_keywords)]
        first_two = lines[:2]

        combined = first_two + keyword_lines + sentiment_lines
        unique_filtered = list(dict.fromkeys(combined))

        return " ".join(unique_filtered)[:1000]

    except Exception:
        return "(본문 추출 실패)"

try:
    with open(save_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["키워드", "제목", "링크", "요약", "블로거명", "게시일", "본문추출"])

        for keyword in keywords:
            query = urllib.parse.quote(keyword)
            url = f"https://openapi.naver.com/v1/search/blog.json?query={query}&display=20"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                result = response.json()
                items = result.get("items", [])
                print(f"[{keyword}] 검색 결과 수: {len(items)}")

                for item in items:
                    title = re.sub(r"<.*?>", "", item.get("title", ""))
                    link = item.get("link", "")
                    description = re.sub(r"<.*?>", "", item.get("description", ""))
                    blogger = item.get("bloggername", "")
                    postdate = item.get("postdate", "")
                    blog_text = extract_blog_content(link)
                    writer.writerow([keyword, title, link, description, blogger, postdate, blog_text])
            else:
                print(f"요청 실패: {keyword}, 코드: {response.status_code}")

    print(f"✅ 모든 데이터를 저장했습니다: {save_path}")
except PermissionError:
    print("❌ 저장 실패: 파일이 열려 있거나 사용 중입니다. Excel 파일을 닫고 다시 실행해주세요.")
except Exception as e:
    print(f"❌ 알 수 없는 오류 발생: {e}")
finally:
    driver.quit()
