import time
import random
import os
from colorama import Fore, Style, init

# 初始化colorama
init()

# 定义emoji常量
EMOJI = {
    'MAIL': '📧',
    'REFRESH': '🔄',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'INFO': 'ℹ️',
    'CODE': '📱'
}

class BrowserControl:
    def __init__(self, browser, translator=None):
        self.browser = browser
        self.translator = translator  # 保存translator
        self.sign_up_url = "https://authenticator.cursor.sh/sign-up"
        self.current_tab = None  # 当前标签页
        self.signup_tab = None   # 注册标签页
        self.email_tab = None    # 邮箱标签页

    def create_new_tab(self):
        """创建新标签页"""
        try:
            # 保存当前标签页
            self.current_tab = self.browser
            
            # 创建新的浏览器实例
            from browser import BrowserManager
            browser_manager = BrowserManager()
            new_browser = browser_manager.init_browser()
            
            # 保存新标签页
            self.signup_tab = new_browser
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('control.create_new_tab_success')}{Style.RESET_ALL}")
            return new_browser
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.create_new_tab_failed', error=str(e))}{Style.RESET_ALL}")
            return None


    def fill_verification_code(self, code):
        """填写验证码"""
        try:
            if not code or len(code) != 6:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.verification_code_format_error')}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('control.fill_verification_code')}...{Style.RESET_ALL}")
            
            # 记住当前标签页（邮箱页面）
            email_tab = self.browser
            
            # 切换回注册页面标签
            self.switch_to_tab(self.signup_tab)
            time.sleep(1)
            
            # 输入验证码
            for digit in code:
                self.browser.actions.input(digit)
                time.sleep(random.uniform(0.1, 0.3))
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('control.verification_code_filled')}{Style.RESET_ALL}")
            
            # 等待页面加载和登录完成
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('control.wait_for_login')}...{Style.RESET_ALL}")
            time.sleep(5)
            
            # 先访问登录页面确保登录状态
            login_url = "https://authenticator.cursor.sh"
            self.browser.get(login_url)
            time.sleep(3)  # 增加等待时间
            
            # 获取cookies（第一次尝试）
            token = self.get_cursor_session_token()
            if not token:
                print(f"{Fore.YELLOW}{EMOJI['ERROR']} {self.translator.get('control.get_token_failed')}...{Style.RESET_ALL}")
                time.sleep(3)
                token = self.get_cursor_session_token()
            
            if token:
                self.save_token_to_file(token)
                
                # 获取到token后再访问设置页面
                settings_url = "https://www.cursor.com/settings"
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('control.get_account_info')}...{Style.RESET_ALL}")
                self.browser.get(settings_url)
                time.sleep(2)
                
                # 获取账户额度信息
                try:
                    usage_selector = (
                        "css:div.col-span-2 > div > div > div > div > "
                        "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
                        "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
                    )
                    usage_ele = self.browser.ele(usage_selector)
                    if usage_ele:
                        usage_info = usage_ele.text
                        total_usage = usage_info.split("/")[-1].strip()
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('control.account_usage_limit')}: {total_usage}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.get_account_usage_failed', error=str(e))}{Style.RESET_ALL}")
            
            # 切换回邮箱页面
            self.switch_to_tab(email_tab)
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.fill_verification_code_failed', error=str(e))}{Style.RESET_ALL}")
            return False 

    def check_and_click_turnstile(self):
        """检查并点击 Turnstile 验证框"""
        try:
            # 等待验证框出现
            time.sleep(1)
            
            # 查找验证框
            verify_checkbox = self.browser.ele('xpath://label[contains(@class, "cb-lb")]//input[@type="checkbox"]')
            if verify_checkbox:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('control.find_turnstile_verification_box')}...{Style.RESET_ALL}")
                verify_checkbox.click()
                time.sleep(2)  # 等待验证完成
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('control.clicked_turnstile_verification_box')}{Style.RESET_ALL}")
                return True
            return False
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['ERROR']} {self.translator.get('control.check_and_click_turnstile_failed', error=str(e))}{Style.RESET_ALL}")
            return False 

    def get_cursor_session_token(self, max_attempts=3, retry_interval=2):
        """获取Cursor会话token"""
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('control.get_cursor_session_token')}...{Style.RESET_ALL}")
        attempts = 0

        while attempts < max_attempts:
            try:
                # 直接从浏览器对象获取cookies
                all_cookies = self.browser.get_cookies()
                
                # 遍历查找目标cookie
                for cookie in all_cookies:
                    if cookie.get("name") == "WorkosCursorSessionToken":
                        token = cookie["value"].split("%3A%3A")[1]
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('control.get_cursor_session_token_success')}: {token}{Style.RESET_ALL}")
                        return token

                attempts += 1
                if attempts < max_attempts:
                    print(f"{Fore.YELLOW}{EMOJI['ERROR']} {self.translator.get('control.get_cursor_session_token_failed', attempts=attempts, retry_interval=retry_interval)}...{Style.RESET_ALL}")
                    time.sleep(retry_interval)
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.reach_max_attempts', max_attempts=max_attempts)}{Style.RESET_ALL}")

            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.get_cookie_failed', error=str(e))}{Style.RESET_ALL}")
                attempts += 1
                if attempts < max_attempts:
                    print(f"{Fore.YELLOW}{EMOJI['ERROR']} {self.translator.get('control.will_retry_in', retry_interval=retry_interval)}...{Style.RESET_ALL}")
                    time.sleep(retry_interval)

        return None

    def save_token_to_file(self, token):
        """保存token到文件"""
        try:
            with open('cursor_tokens.txt', 'a', encoding='utf-8') as f:
                f.write(f"Token: {token}\n")
                f.write("-" * 50 + "\n")
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('control.token_saved_to_file')}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('control.save_token_failed', error=str(e))}{Style.RESET_ALL}") 