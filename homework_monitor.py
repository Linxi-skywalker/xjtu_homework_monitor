import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ====================== 账号配置（只写一次） ======================
CONFIG = {
    "m60": {
        "user": "c++面向对象程序设计账号",
        "pass": "c++面向对象程序设计密码"
    },
    "m144": {
        "user": "算法分析与设计账号",
        "pass": "算法分析与设计密码"
    }
}

# ====================== 推送 & Cookie 配置 ======================
COOKIE_LMS = "思源学堂的 Cookie"
SCT_SEND_KEY = "你的推送key"  # <--- 推送 key 写这里！
CHECK_INTERVAL = 3600
# ==============================================================

PUSHED_FILE = "pushed_homework.txt"

def clear_pushed():
    with open(PUSHED_FILE, "w", encoding="utf-8") as f:
        f.write("")

def load_pushed():
    try:
        with open(PUSHED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def mark_pushed(uid):
    with open(PUSHED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{uid}\n")

def send_wechat(title, content):
    if not SCT_SEND_KEY:
        print("📩 未配置推送")
        return
    url = f"https://sctapi.ftqq.com/{SCT_SEND_KEY}.send"
    try:
        requests.post(url, json={"title": title, "desp": content}, timeout=8)
        print("✅ 微信推送成功")
    except:
        print("❌ 推送失败")

# ---------------------- LMS 作业 ----------------------
def get_lms():
    headers = {
        "Cookie": COOKIE_LMS,
        "User-Agent": "Mozilla/5.0"
    }

    try:
        print("🔗 LMS 使用 Cookie 直连...")
        data = requests.get("https://lms.xjtu.edu.cn/api/todos", headers=headers, timeout=8).json()

        res = []
        for item in data.get("todo_list", []):
            try:
                utc_time_str = item["end_time"]
                utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
                beijing_time = utc_time + timedelta(hours=8)
                dead = beijing_time.strftime("%Y-%m-%d %H:%M")
            except:
                dead = "无截止时间"

            res.append({
                "id": f"LMS_{item['id']}",
                "source": "LMS",
                "course": item.get("course_name", "未知课程"),
                "title": item.get("title", "未知任务"),
                "deadline": dead
            })

        print(f"✅ LMS 成功获取 {len(res)} 个待办")
        return res

    except Exception as e:
        print(f"❌ LMS 错误：{e}")
        return []

# ---------------- Moodle60 ----------------
def get_m60():
    user = CONFIG["m60"]["user"]
    pwd = CONFIG["m60"]["pass"]

    if not user or not pwd:
        return []

    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"

    try:
        login_url = "http://202.117.10.60/moodle/login/index.php"
        r = s.get(login_url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        token_tag = soup.find("input", {"name": "logintoken"})
        token = token_tag["value"] if token_tag else ""

        s.post(login_url, data={
            "username": user,
            "password": pwd,
            "logintoken": token
        }, timeout=10)

        r = s.get("http://202.117.10.60/moodle/mod/assignment/index.php?id=228", timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_="generaltable")
        if not table:
            print("❌ Moodle60 登录失败")
            return []

        res = []
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            name = tds[1].get_text(strip=True)
            tstr = tds[3].get_text(strip=True)
            submit = tds[4].get_text(strip=True)
            score = tds[5].get_text(strip=True)

            if "2026" not in tstr or tstr == "-":
                continue
            if submit != "" or score != "-":
                continue

            res.append({
                "id": f"MOODLE_{hash(name + tstr)}",
                "source": "Moodle60",
                "course": "C++面向对象程序设计",
                "title": name,
                "deadline": tstr
            })

        print(f"✅ Moodle60: {len(res)} 个")
        return res

    except Exception as e:
        print("❌ Moodle60错误:", e)
        return []

# ---------------- Moodle144----------------
def get_m144():
    user = CONFIG["m144"]["user"]
    pwd = CONFIG["m144"]["pass"]

    if not user or not pwd:
        return []

    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"

    try:
        login_url = "http://202.117.10.144/md311/login/index.php"
        r = s.get(login_url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        token_tag = soup.find("input", {"name": "logintoken"})
        token = token_tag["value"] if token_tag else ""

        login_res = s.post(login_url, data={
            "username": user,
            "password": pwd,
            "logintoken": token
        }, timeout=10)

        r = s.get("http://202.117.10.144/md311/course/view.php?id=29", timeout=10)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        res = []

        activities = soup.find_all("li", class_="activity")
        for act in activities:
            name_elem = act.find("span", class_="instancename")
            if not name_elem:
                continue
            title = name_elem.get_text(strip=True).split(" ")[0]

            time_info = act.find("div", {"data-region": "activity-dates"})
            deadline = "无截止时间"
            if time_info:
                time_text = time_info.get_text(strip=True)
                if "关闭:" in time_text:
                    deadline_part = time_text.split("关闭:")[-1].strip()
                    deadline = f"截止：{deadline_part}"

            complete_btn = act.find("button", {"data-action": "toggle-manual-completion"})
            if complete_btn and "标记完成" in complete_btn.get_text(strip=True):
                res.append({
                    "id": f"MOODLE3_{hash(title + deadline)}",
                    "source": "Moodle144",
                    "course": "2026算法分析与设计（赖欣）",
                    "title": title,
                    "deadline": deadline,
                })

        print(f"✅ Moodle144: {len(res)} 个")
        return res

    except Exception as e:
        print(f"❌ Moodle144错误: {e}")
        return []

# ---------------- 主程序 ----------------
def run():
    print("\n🔍 检查作业...\n")
    pushed = load_pushed()

    all_tasks = []
    all_tasks += get_lms()
    all_tasks += get_m60()
    all_tasks += get_m144()

    print("\n" + "="*50)
    msg = ""
    for t in all_tasks:
        line = f"[{t['source']}] {t['course']}\n📝 {t['title']}\n⏰ {t['deadline']}\n"
        print(line)
        print("-"*50)
        msg += line + "\n"

    new_tasks = [t for t in all_tasks if t.get("id") not in pushed]
    if new_tasks:
        send_wechat("📚 待完成作业提醒", msg)
        for t in new_tasks:
            mark_pushed(t["id"])

if __name__ == "__main__":
    clear_pushed()
    while True:
        run()
        time.sleep(CHECK_INTERVAL)
