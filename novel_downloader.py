#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说下载器 - 支持下载小说并转换为EPUB或TXT格式
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import os
from ebooklib import epub
from urllib.parse import urljoin, urlparse
import argparse

# 尝试导入Selenium，如果未安装则设为None
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, WebDriverException
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False

class NovelDownloader:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.chapters = []
        self.novel_title = ""
        self.novel_author = ""
        
    def get_page(self, url, retry=3):
        """获取网页内容，带重试机制"""
        for i in range(retry):
            try:
                response = self.session.get(url, timeout=10)
                response.encoding = 'utf-8'
                if response.status_code == 200:
                    return response.text
            except Exception as e:
                print(f"获取页面失败 (尝试 {i+1}/{retry}): {e}")
                if i < retry - 1:
                    time.sleep(2)
        return None
    
    def get_page_with_selenium(self, url):
        """使用Selenium获取完整页面（包括JavaScript渲染的内容）"""
        if not SELENIUM_AVAILABLE:
            return None
        
        try:
            print("正在使用Selenium浏览器获取完整页面...")
            driver = None
            
            # 首先尝试使用Edge浏览器（Windows系统通常自带）
            try:
                print("尝试使用Edge浏览器...")
                from selenium.webdriver.edge.options import Options as EdgeOptions
                from selenium.webdriver.edge.service import Service as EdgeService
                try:
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    edge_options = EdgeOptions()
                    edge_options.add_argument('--headless')
                    edge_options.add_argument('--no-sandbox')
                    edge_options.add_argument('--disable-dev-shm-usage')
                    edge_options.add_argument('--disable-gpu')
                    edge_options.add_argument('--window-size=1920,1080')
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    driver = webdriver.Edge(service=service, options=edge_options)
                    print("成功启动Edge浏览器")
                except:
                    # 尝试直接使用Edge（如果已安装）
                    edge_options = EdgeOptions()
                    edge_options.add_argument('--headless')
                    edge_options.add_argument('--no-sandbox')
                    edge_options.add_argument('--disable-dev-shm-usage')
                    driver = webdriver.Edge(options=edge_options)
                    print("成功启动Edge浏览器（直接模式）")
            except Exception as e:
                print(f"无法使用Edge浏览器: {e}")
                # 如果Edge失败，尝试Chrome
                try:
                    print("尝试使用Chrome浏览器...")
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                    
                    if WEBDRIVER_MANAGER_AVAILABLE:
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        driver = webdriver.Chrome(options=chrome_options)
                    print("成功启动Chrome浏览器")
                except Exception as e2:
                    print(f"无法使用Chrome浏览器: {e2}")
                    return None
            
            if not driver:
                return None
            
            try:
                driver.get(url)
                
                # 等待页面加载
                time.sleep(2)
                
                # 尝试点击"展开列表"、"查看目录"或"更多章节"按钮
                try:
                    expand_selectors = [
                        "//a[contains(text(), '展开完整列表') or contains(text(), '查看目录') or contains(text(), '全部章节') or contains(text(), '更多章节') or contains(text(), '展开全部') or contains(text(), '查看全部')]",
                        "//button[contains(text(), '展开完整列表') or contains(text(), '查看目录') or contains(text(), '全部章节') or contains(text(), '更多章节') or contains(text(), '展开全部') or contains(text(), '查看全部')]",
                        "//*[contains(text(), '展开完整列表') or contains(text(), '查看目录') or contains(text(), '全部章节') or contains(text(), '更多章节') or contains(text(), '展开全部') or contains(text(), '查看全部')]",
                    ]

                    clicked_any = False
                    for selector in expand_selectors:
                        for _ in range(3):
                            try:
                                button = WebDriverWait(driver, 2).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                                if button:
                                    print(f"找到展开按钮，正在点击 ({selector})...")
                                    driver.execute_script("arguments[0].click();", button)
                                    time.sleep(2)
                                    clicked_any = True
                                else:
                                    break
                            except TimeoutException:
                                break

                    if not clicked_any:
                        print("未找到明确的展开按钮，尝试直接执行JavaScript展开...")
                        driver.execute_script("""
                            var candidates = [];
                            var all = document.querySelectorAll('a, button');
                            for (var i = 0; i < all.length; i++) {
                                var text = (all[i].textContent || all[i].innerText || '').trim();
                                if (text && /展开|查看目录|全部章节|更多章节|展开全部|查看全部/.test(text)) {
                                    candidates.push(all[i]);
                                }
                            }
                            for (var j = 0; j < candidates.length; j++) {
                                try {
                                    candidates[j].click();
                                } catch (e) {
                                    continue;
                                }
                            }
                        """)
                        time.sleep(2)

                    # 滚动页面，触发可能的懒加载章节列表
                    driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
                    time.sleep(2)
                    driver.execute_script('window.scrollTo(0, 0);')
                    time.sleep(1)

                except Exception as e:
                    print(f"点击展开按钮时出错: {e}")
                
                # 获取完整页面HTML
                html = driver.page_source
                return html
                
            finally:
                if driver:
                    driver.quit()
                    
        except WebDriverException as e:
            print(f"Selenium错误: {e}")
            print("提示: 请确保已安装Chrome浏览器和ChromeDriver")
            return None
        except Exception as e:
            print(f"使用Selenium获取页面时出错: {e}")
            return None
    
    def parse_chapter_list(self):
        """解析章节列表"""
        print("正在获取章节列表...")
        
        # 首先尝试使用Selenium获取完整页面
        html = None
        if SELENIUM_AVAILABLE:
            html = self.get_page_with_selenium(self.base_url)
        
        # 如果Selenium失败，使用普通方法
        if not html:
            print("使用普通方法获取页面...")
            html = self.get_page(self.base_url)
        
        if not html:
            print("无法获取章节列表页面")
            return False
        
        # 保存原始HTML用于后续提取
        original_html = html
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找"展开完整列表"或类似的链接
        # 方法1: 查找包含"展开"文本的链接
        expand_text = soup.find(string=re.compile(r'展开.*列表|展开完整'))
        expand_link = None
        
        if expand_text:
            # 查找包含这个文本的链接
            parent = expand_text.find_parent('a')
            if parent and parent.get('href'):
                expand_link = parent
            else:
                # 查找附近的链接
                for elem in expand_text.find_parents():
                    if elem.name == 'a' and elem.get('href'):
                        expand_link = elem
                        break
        
        # 方法2: 直接查找所有包含"展开"的链接
        if not expand_link:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                text = link.get_text().strip()
                if re.search(r'展开.*列表|展开完整|展开全部', text):
                    expand_link = link
                    break
        
        # 如果找到展开链接，尝试访问它
        expand_link_found = False
        if expand_link:
            expand_href = expand_link.get('href', '')
            if expand_href:
                # 检查是否是JavaScript链接
                if expand_href.startswith('javascript:'):
                    print(f"找到展开链接（JavaScript）: {expand_link.get_text().strip()}")
                    print("尝试从页面源代码中提取隐藏的章节数据...")
                    
                    # 方法1: 从script标签中提取章节数据
                    scripts = soup.find_all('script')
                    for script in scripts:
                        script_text = script.string
                        if script_text:
                            # 查找可能包含章节列表的JavaScript变量或数据
                            # 尝试匹配章节URL模式
                            chapter_urls = re.findall(r'["\']([^"\']*xs-\d+/\d+\.html[^"\']*)["\']', script_text)
                            if chapter_urls:
                                print(f"从JavaScript中找到 {len(chapter_urls)} 个章节URL")
                                for url in chapter_urls:
                                    full_url = urljoin(self.base_url, url)
                                    # 尝试从script中提取对应的标题
                                    # 这里简化处理，使用URL作为标题的一部分
                                    self.chapters.append({
                                        'title': f"章节 {url.split('/')[-1].replace('.html', '')}",
                                        'url': full_url
                                    })
                    
                    # 方法2: 查找可能包含章节数据的data属性或隐藏元素
                    hidden_elements = soup.find_all(attrs={'style': re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden')})
                    for elem in hidden_elements:
                        links = elem.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if re.search(r'xs-\d+/\d+\.html|/\d+\.html', href):
                                full_url = urljoin(self.base_url, href)
                                title = link.get_text().strip()
                                if title:
                                    self.chapters.append({
                                        'title': title,
                                        'url': full_url
                                    })
                    
                    # 方法3: 查找所有可能被CSS隐藏的章节链接
                    print("查找所有章节链接（包括可能被隐藏的）...")
                    expand_link_found = True
                else:
                    expand_url = urljoin(self.base_url, expand_href)
                    print(f"找到展开链接: {expand_link.get_text().strip()}")
                    print(f"正在访问: {expand_url}")
                    expand_html = self.get_page(expand_url)
                    if expand_html:
                        # 使用展开后的页面内容
                        html = expand_html
                        soup = BeautifulSoup(html, 'html.parser')
                        print("已获取完整章节列表页面")
                        expand_link_found = True
                    else:
                        print("警告: 无法访问展开链接，将使用当前页面的章节列表")
        
        # 尝试通过API获取完整章节列表
        novel_id_match = re.search(r'xs-(\d+)', self.base_url)
        novel_id = novel_id_match.group(1) if novel_id_match else None
        
        if novel_id and (not expand_link_found or len(self.chapters) < 50):
            print("尝试通过API获取完整章节列表...")
            # 尝试常见的API端点
            api_urls = [
                f"https://www.qb5.io/xs-{novel_id}/chapterlist.html",
                f"https://www.qb5.io/xs-{novel_id}/chapters.html",
                f"https://www.qb5.io/api/chapter/list?book={novel_id}",
            ]
            
            for api_url in api_urls:
                try:
                    print(f"尝试API: {api_url}")
                    api_response = self.get_page(api_url)
                    if api_response:
                        api_soup = BeautifulSoup(api_response, 'html.parser')
                        api_links = api_soup.find_all('a', href=re.compile(r'xs-\d+/\d+\.html|/\d+\.html'))
                        if len(api_links) > len(self.chapters):
                            html = api_response
                            soup = api_soup
                            original_html = api_response
                            print(f"通过API找到 {len(api_links)} 个章节")
                            self.chapters = []  # 清空，重新解析
                            break
                except:
                    continue
        
        # 如果没找到展开链接或展开链接是JavaScript，尝试访问可能的章节列表页面
        # 例如: https://www.qb5.io/xs-66401/ 可能有一个章节列表页面
        if not expand_link_found or len(self.chapters) < 50:
            print("尝试访问可能的完整章节列表页面...")
            # 尝试常见的章节列表URL模式
            base_path = urlparse(self.base_url).path.rstrip('/')
            
            possible_urls = []
            if novel_id:
                # 尝试不同的URL模式
                possible_urls = [
                    f"https://www.qb5.io/xs-{novel_id}/",  # 主页
                    f"https://www.qb5.io/xs-{novel_id}/all.html",  # all页面
                    f"https://www.qb5.io/xs-{novel_id}/list.html",  # list页面
                    f"https://www.qb5.io/xs-{novel_id}/?all=1",  # 带参数
                    f"https://www.qb5.io/xs-{novel_id}/index.html",  # index页面
                    f"https://www.qb5.io/xs-{novel_id}/chapterlist.html",  # 章节列表页面
                ]
            else:
                possible_urls = [
                    self.base_url + '?all=1',  # 带参数
                    base_path + '/all.html',   # all页面
                    base_path + '/list.html',  # list页面
                    base_path + '/index.html',  # index页面
                    base_path + '/chapterlist.html',  # 章节列表页面
                ]
            
            current_chapter_count = len(self.chapters)
            for test_url in possible_urls:
                print(f"尝试访问: {test_url}")
                test_html = self.get_page(test_url)
                if test_html:
                    test_soup = BeautifulSoup(test_html, 'html.parser')
                    # 检查这个页面是否有更多章节
                    test_links = test_soup.find_all('a', href=re.compile(r'xs-\d+/\d+\.html|/\d+\.html'))
                    if len(test_links) > current_chapter_count:
                        html = test_html
                        soup = test_soup
                        original_html = test_html
                        print(f"在 {test_url} 找到 {len(test_links)} 个章节链接")
                        # 清空之前找到的章节，使用新页面的
                        self.chapters = []
                        break
        
        # 获取小说标题和作者
        title_elem = soup.find('h1')
        if title_elem:
            self.novel_title = title_elem.get_text().strip()
            print(f"小说标题: {self.novel_title}")
        
        # 查找作者信息
        author_pattern = soup.find(string=re.compile('作者'))
        if author_pattern:
            author_elem = author_pattern.find_parent()
            if author_elem:
                self.novel_author = author_elem.get_text().replace('作者:', '').replace('作者：', '').strip()
                print(f"作者: {self.novel_author}")
        
        # 查找章节列表
        chapter_list = []
        
        # 方法1: 查找"章节目录"标题后的所有链接
        chapter_title = soup.find(string=re.compile('章节目录|目录'))
        if chapter_title:
            print("找到'章节目录'标题，正在解析...")
            parent = chapter_title.find_parent()
            if parent:
                # 查找父元素后面的所有链接
                for sibling in parent.find_next_siblings():
                    if hasattr(sibling, 'find_all'):
                        links = sibling.find_all('a', href=True)
                        if links:
                            chapter_list.extend(links)
                # 也在父元素内查找
                links = parent.find_all('a', href=True)
                if links:
                    chapter_list.extend(links)
                # 查找父元素的父元素（可能章节列表在更大的容器中）
                grandparent = parent.find_parent()
                if grandparent:
                    links = grandparent.find_all('a', href=True)
                    if links and len(links) > len(chapter_list):
                        chapter_list = links
        
        # 方法2: 查找所有包含章节链接的容器（更宽松的匹配，包括隐藏的）
        if not chapter_list or len(chapter_list) < 5:
            print("尝试方法2: 查找章节容器（包括可能隐藏的）...")
            # 查找所有可能的容器，包括可能被CSS隐藏的
            containers = soup.find_all(['div', 'ul', 'dl', 'ol'])
            for container in containers:
                links = container.find_all('a', href=True)
                # 检查是否包含章节链接模式
                chapter_links = []
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    
                    # 跳过明显的非章节链接
                    if any(skip in href.lower() for skip in ['javascript:', '#', 'mailto:', 'tel:', '展开']):
                        continue
                    
                    # 匹配各种章节URL模式
                    if (re.search(r'xs-\d+/\d+\.html|/\d+\.html|/\d+/\d+\.html', href) or
                        (text and (re.search(r'第.*章|第.*节|^\d+', text) or 
                                  (len(text) > 2 and len(text) < 50 and not re.search(r'首页|搜索|登录|注册|展开', text))))):
                        chapter_links.append(link)
                
                if len(chapter_links) > 5:  # 如果找到多个章节链接
                    chapter_list = chapter_links
                    print(f"在容器中找到 {len(chapter_list)} 个章节链接")
                    break
        
        # 方法3: 从原始HTML中直接提取所有章节URL（最彻底的方法）
        if not chapter_list or len(chapter_list) < 50:
            print("尝试方法3: 从原始HTML中提取所有章节URL...")
            # 直接从HTML文本中提取章节URL，不依赖BeautifulSoup的解析
            # 这样可以找到所有URL，包括可能被JavaScript动态加载的
            html_text = original_html
            
            # 提取所有章节URL模式
            # 匹配: /xs-66401/1.html, /xs-66401/123.html 等
            novel_id_match = re.search(r'xs-(\d+)', self.base_url)
            if novel_id_match:
                novel_id = novel_id_match.group(1)
                # 匹配该小说的所有章节URL
                chapter_url_pattern = rf'/xs-{novel_id}/(\d+)\.html'
                chapter_urls = re.findall(chapter_url_pattern, html_text)
                
                if chapter_urls:
                    print(f"从HTML源代码中找到 {len(set(chapter_urls))} 个唯一的章节编号")
                    # 去重并排序
                    unique_chapter_nums = sorted(set(int(num) for num in chapter_urls), key=int)
                    
                    # 为每个章节创建链接对象（模拟）
                    for chapter_num in unique_chapter_nums:
                        chapter_url = f"/xs-{novel_id}/{chapter_num}.html"
                        full_url = urljoin(self.base_url, chapter_url)
                        
                        # 尝试从HTML中找到对应的标题
                        # 查找包含这个URL的链接元素
                        link_elem = soup.find('a', href=re.compile(re.escape(chapter_url)))
                        if link_elem:
                            title = link_elem.get_text().strip()
                        else:
                            # 如果找不到，使用章节号作为标题
                            title = f"第{chapter_num}章"
                        
                        # 创建模拟的链接对象
                        class MockLink:
                            def __init__(self, href, text):
                                self.href = href
                                self.text = text
                            def get(self, key, default=None):
                                if key == 'href':
                                    return self.href
                                return default
                            def get_text(self):
                                return self.text
                        
                        chapter_list.append(MockLink(chapter_url, title))
            
            # 如果上面的方法没找到足够多的章节，继续使用原来的方法
            if len(chapter_list) < 50:
                print("方法3找到的章节较少，继续使用方法4...")
                # 查找所有链接，包括可能被CSS隐藏的
                all_links = soup.find_all('a', href=True)
                print(f"页面中共有 {len(all_links)} 个链接，正在筛选章节链接...")
                
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text().strip()
                    
                    # 跳过明显的非章节链接
                    if any(skip in href.lower() for skip in ['javascript:', '#', 'mailto:', 'tel:']):
                        continue
                    
                    # 跳过包含展开、更多等文本的链接
                    if text and re.search(r'展开|更多|完整|全部|查看全部', text):
                        continue
                    
                    # 更宽松的匹配规则
                    if href:
                        # 匹配章节URL模式: 
                        # /xs-66401/1.html
                        # /xs-66401/123.html
                        # /123.html
                        # /123/456.html
                        if (re.search(r'xs-\d+/\d+\.html', href) or  # /xs-66401/1.html
                            re.search(r'/\d+\.html$', href) or        # /1.html
                            re.search(r'/\d+/\d+\.html', href)):      # /123/456.html
                            chapter_list.append(link)
                        # 或者链接文本看起来像章节标题
                        elif text and (re.search(r'第.*章|第.*节|^\d+', text) or 
                                      (len(text) > 2 and len(text) < 50 and not re.search(r'首页|搜索|登录|注册|展开|更多', text))):
                            # 检查href是否包含数字（可能是章节）
                            # 但要确保不是其他类型的链接
                            if re.search(r'\d+', href) and not re.search(r'\.(jpg|png|gif|css|js|ico)$', href):
                                chapter_list.append(link)
            
            print(f"方法3和方法4共找到 {len(chapter_list)} 个可能的章节链接")

        # 方法5: 全局提取章节链接，进一步补充可能遗漏的章节
        if not chapter_list or len(chapter_list) < 200:
            print("尝试方法5: 全局提取章节链接...")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '').strip()
                text = link.get_text().strip()

                if not href:
                    continue
                if any(skip in href.lower() for skip in ['javascript:', '#', 'mailto:', 'tel:', 'login', 'search', 'register', 'javascript']):
                    continue
                if re.search(r'\.(jpg|png|gif|css|js|ico|svg|pdf)$', href, re.I):
                    continue

                is_chapter_url = bool(re.search(r'(xs-\d+/\d+\.html|/\d+\.html|/\d+/\d+\.html|chapterlist\.html|all\.html|list\.html)$', href))
                is_chapter_text = bool(text and re.search(r'第.*章|第.*节|^\d+', text))

                if is_chapter_url or is_chapter_text:
                    chapter_list.append(link)

            chapter_list = list(dict.fromkeys(chapter_list))
            print(f"方法5共找到 {len(chapter_list)} 个可能的章节链接")

        # 去重并排序
        seen = set()
        for link in chapter_list:
            href = link.get('href', '')
            if not href:
                continue
            
            # 转换为绝对URL
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                full_url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(self.base_url, href)
            
            # 去重
            if full_url not in seen:
                title = link.get_text().strip()
                if title:  # 只要有标题就添加
                    self.chapters.append({
                        'title': title,
                        'url': full_url
                    })
                    seen.add(full_url)
        
        # 按URL中的数字排序
        def sort_key(ch):
            # 提取URL中的所有数字
            numbers = re.findall(r'\d+', ch['url'])
            if not numbers:
                return 0

            # 如果能从base_url中识别出novel_id，优先选择紧随novel_id之后的数字作为章节号
            nid = None
            m = re.search(r'xs-(\d+)', self.base_url)
            if m:
                nid = m.group(1)

            if nid:
                # 在URL中找到 'xs-<nid>' 出现位置，并在其后寻找第一个数字（通常是章节号）
                pos = ch['url'].find('xs-' + nid)
                if pos != -1:
                    substr = ch['url'][pos + len('xs-' + nid):]
                    m2 = re.search(r'(\d+)\.html', substr)
                    if m2:
                        try:
                            return int(m2.group(1))
                        except:
                            pass

            # 如果有多个数字，选择位数最长的数字（通常为章节编号而非页码）
            if len(numbers) > 1:
                candidates = [int(n) for n in numbers]
                return max(candidates, key=lambda x: len(str(x)))

            # 否则使用唯一数字（通常为章节号）
            return int(numbers[-1])
        
        self.chapters.sort(key=sort_key)
        
        print(f"从目录页找到 {len(self.chapters)} 个章节")
        if len(self.chapters) > 0:
            print(f"前3个章节示例: {[ch['title'] for ch in self.chapters[:3]]}")

        # 打印章节总数
        print(f"共解析到 {len(self.chapters)} 章，即将开始下载")
        print(f"前3章: {[ch['title'] for ch in self.chapters[:3]]}")

        return len(self.chapters) > 0

    @staticmethod
    def _chapter_num_from_url(url):
        """从章节URL中提取章节编号（ du-1_2.html → 1, 123_2.html → 123, 1.html → 1 ）"""
        path = url.rstrip('/')
        last_seg = path.split('/')[-1] if '/' in path else path
        if last_seg.endswith('.html'):
            last_seg = last_seg[:-5]
        # 去掉分页后缀 _N（如 du-1_2 → du-1, 123_2 → 123）
        last_seg = re.sub(r'_\d+$', '', last_seg)
        # 情况1: 纯数字
        if last_seg.isdigit():
            return int(last_seg)
        # 情况2: 文字-数字 或 文字_数字（如 du-1 → 1）
        m = re.search(r'[_-](\d+)$', last_seg)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _is_pagination_url(url):
        """判断是否为同章分页URL（如 du-1_2.html, 123_2.html）"""
        path = url.rstrip('/')
        last = path.split('/')[-1] if '/' in path else path
        # 仅下划线分页，如 du-1_2.html → True，du-1.html → False
        return bool(re.search(r'_\d+\.html$', last))

    def find_next_chapter_url(self, soup, current_url):
        """查找章节正文页中的下一章链接（用于章节间导航）"""
        current_chapter = self._chapter_num_from_url(current_url)

        # 方法1: 找明确的"下一章"文本
        for link in soup.find_all('a', href=True):
            text = (link.get_text() or '').strip()
            href = link.get('href', '')
            if href.startswith('javascript:'):
                continue
            if re.search(r'^(下一章|下章|后一章|后章|下一章[>»]?|next\s*chapter)$', text, re.I):
                return urljoin(current_url, href)

        # 方法2: 找"下一页"文本链接，排除同章分页
        for link in soup.find_all('a', href=True):
            text = (link.get_text() or '').strip()
            href = link.get('href', '')
            if href.startswith('javascript:'):
                continue
            if re.search(r'^(下一页|下页|后一页|后页|下一页[>»]?|next\s*page)$', text, re.I):
                target_url = urljoin(current_url, href)
                target_chapter = self._chapter_num_from_url(target_url)
                if target_chapter is not None and current_chapter is not None and target_chapter > current_chapter and not self._is_pagination_url(target_url):
                    return target_url

        # 方法3: 查找所有符合章节URL模式的链接，找 chapter_num = current + 1
        if current_chapter is not None:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('javascript:'):
                    continue
                target_url = urljoin(current_url, href)
                tc = self._chapter_num_from_url(target_url)
                if tc is not None and tc == current_chapter + 1:
                    return target_url

        # 方法4: 找所有符合章节URL模式的链接中 chapter_num 最小的且 > current
        if current_chapter is not None:
            candidates = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('javascript:'):
                    continue
                target_url = urljoin(current_url, href)
                tc = self._chapter_num_from_url(target_url)
                if tc is not None and tc > current_chapter:
                    candidates.append((tc, target_url))
            if candidates:
                candidates.sort()
                best = candidates[0]
                if best[0] == current_chapter + 1:
                    return best[1]

        return None

    def find_next_page_url(self, soup, current_url):
        """查找章节正文页中的同章分页链接（如 123_2.html），排除章间导航"""
        current_chapter = self._chapter_num_from_url(current_url)

        # 方法1: rel=next 且 URL 是分页模式或同一章节号
        next_link = soup.find('a', rel=re.compile('next', re.I))
        if next_link and next_link.get('href'):
            href = next_link.get('href')
            if not href.startswith('javascript:'):
                target_url = urljoin(current_url, href)
                # 只有同章分页才跟随
                if self._is_pagination_url(target_url):
                    return target_url
                tc = self._chapter_num_from_url(target_url)
                if tc is not None and tc == current_chapter:
                    return target_url

        # 方法2: 找"下一页"链接，但只接受同章分页
        for link in soup.find_all('a', href=True):
            text = (link.get_text() or '').strip()
            if not text:
                continue
            if re.search(r'^(下一页|下页|后一页|后页|下一页[>»]?|next\s*page)$', text, re.I):
                href = link['href']
                if href.startswith('javascript:'):
                    continue
                target_url = urljoin(current_url, href)
                if self._is_pagination_url(target_url):
                    return target_url
                tc = self._chapter_num_from_url(target_url)
                if tc is not None and current_chapter is not None and tc == current_chapter:
                    return target_url

        return None

    def extract_content_from_soup(self, soup):
        """尝试从章节页面提取正文内容"""
        content = None

        content_div = soup.find('div', id=re.compile('content|text|chapter|booktext', re.I))
        if content_div:
            for script in content_div(["script", "style", "noscript"]):
                script.decompose()
            content = content_div.get_text(separator='\n')

        if not content or len(content.strip()) < 100:
            content_div = soup.find('div', class_=re.compile('content|text|chapter|novel|booktext', re.I))
            if content_div:
                for script in content_div(["script", "style", "noscript"]):
                    script.decompose()
                content = content_div.get_text(separator='\n')

        if not content or len(content.strip()) < 100:
            divs = soup.find_all('div')
            max_len = 0
            best_div = None
            for div in divs:
                div_id = div.get('id', '')
                div_class = ' '.join(div.get('class', []))
                if any(keyword in (div_id + div_class).lower() for keyword in ['header', 'footer', 'nav', 'menu', 'sidebar', 'ad']):
                    continue
                text = div.get_text(separator='\n')
                if len(text) > max_len and len(text) > 100:
                    max_len = len(text)
                    best_div = div
            if best_div:
                for script in best_div(["script", "style", "noscript"]):
                    script.decompose()
                content = best_div.get_text(separator='\n')

        if content:
            return self.clean_content(content)
        return None
    
    def clean_content(self, text):
        """清理文本内容，去除广告和无关内容"""
        if not text:
            return ""
        
        # 去除常见的广告关键词
        ad_keywords = [
            '全本小说网', 'www.qb5.io', 'qb5.io',
            '请记住本站', '本站网址', '手机阅读',
            '最新章节', '无弹窗', '清爽阅读',
            '笔趣阁', '顶点小说', '起点中文网',
            '推荐票', '月票', '打赏',
            '上一章', '下一章', '返回目录',
            '加入书签', '返回书页'
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过包含广告关键词的行
            is_ad = False
            for keyword in ad_keywords:
                if keyword in line:
                    is_ad = True
                    break
            
            if is_ad:
                continue
            
            # 跳过过短的行（可能是导航或广告）
            if len(line) < 5:
                continue
            
            # 跳过看起来像URL的行
            if re.match(r'https?://', line):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def get_chapter_content(self, chapter_url):
        """获取章节内容"""
        current_url = chapter_url
        visited_urls = set()
        content_parts = []
        page_count = 0

        while current_url and current_url not in visited_urls and page_count < 20:
            visited_urls.add(current_url)
            html = self.get_page(current_url)
            if not html:
                break

            soup = BeautifulSoup(html, 'html.parser')
            content = self.extract_content_from_soup(soup)
            if content:
                content_parts.append(content)
            else:
                break

            next_page_url = self.find_next_page_url(soup, current_url)
            if not next_page_url:
                break

            if next_page_url in visited_urls:
                break

            page_count += 1
            current_url = next_page_url
            time.sleep(0.8)

        if content_parts:
            return "\n\n".join(content_parts)
        return None
    
    def download_all_chapters(self):
        """下载所有章节（基于列表）"""
        print(f"开始下载 {len(self.chapters)} 个章节...")
        for i, chapter in enumerate(self.chapters, 1):
            print(f"正在下载 [{i}/{len(self.chapters)}]: {chapter['title']}")
            content = self.get_chapter_content(chapter['url'])
            if content:
                chapter['content'] = content
            else:
                print(f"  警告: 无法获取章节内容")
                chapter['content'] = f"[此章节内容获取失败]"
            
            # 避免请求过快
            time.sleep(0.5)

    def navigate_and_download_all(self, progress_callback=None, stop_check=None,
                                   pause_check=None, pause_save_callback=None):
        """
        从第一个章节开始，通过'下一页'导航，边导航边下载所有章节。
        按真实阅读顺序构建章节列表。
        """
        if not self.chapters:
            print("没有起始章节")
            return 0

        first_url = self.chapters[0]['url']
        self.chapters = []  # 清空，按导航顺序重建

        current_url = first_url
        visited_urls = set()
        downloaded = 0

        while current_url and current_url not in visited_urls:
            if stop_check and stop_check():
                print("下载已终止")
                break

            # 暂停处理：保存已下载内容并等待
            if pause_check and pause_check():
                if downloaded > 0 and pause_save_callback:
                    pause_save_callback(downloaded)
                print("下载已暂停，等待继续...")
                while pause_check and pause_check():
                    if stop_check and stop_check():
                        break
                    time.sleep(0.5)
                if stop_check and stop_check():
                    print("下载已终止")
                    break
                print("继续下载...")

            visited_urls.add(current_url)
            downloaded += 1

            html = self.get_page(current_url)
            if not html:
                print(f"  无法访问: {current_url}")
                break

            soup = BeautifulSoup(html, 'html.parser')

            # 提取标题
            title = None
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    t = title_tag.get_text().strip()
                    for sep in [' - ', ' – ', '—', '_', '|']:
                        if sep in t:
                            t = t.split(sep)[0].strip()
                    title = t
            if not title:
                title = f"第{downloaded}章"

            print(f"正在下载第 {downloaded} 章: {title}")

            # 提取正文（含同章分页）
            content = self.extract_content_from_soup(soup)
            if content:
                page_url = self.find_next_page_url(soup, current_url)
                while page_url and page_url not in visited_urls:
                    page_html = self.get_page(page_url)
                    if page_html:
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        page_content = self.extract_content_from_soup(page_soup)
                        if page_content:
                            content += "\n\n" + page_content
                        next_page = self.find_next_page_url(page_soup, page_url)
                        if next_page and next_page != page_url:
                            page_url = next_page
                            time.sleep(0.8)
                        else:
                            break
                    else:
                        break
                    time.sleep(0.8)
            else:
                content = "[此章节内容获取失败]"
                print(f"  警告: 无法获取章节内容")

            self.chapters.append({
                'title': title,
                'url': current_url,
                'content': content
            })

            # 去除正文开头多余的标题（HTML 的 h1 也被提取进来了）
            if content:
                lines = content.split('\n', 1)
                if lines[0].strip() == title:
                    self.chapters[-1]['content'] = lines[1].strip() if len(lines) > 1 else ''

            if progress_callback:
                progress_callback(downloaded, title)

            # 找下一章
            next_url = self.find_next_chapter_url(soup, current_url)
            if not next_url or next_url in visited_urls:
                break

            current_url = next_url
            time.sleep(0.8)

        print(f"下载完成，共 {downloaded} 章")
        return downloaded
    
    def save_as_txt(self, filename):
        """保存为TXT格式"""
        print(f"正在保存为TXT格式: {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入标题和作者
            f.write(f"{self.novel_title}\n")
            if self.novel_author:
                f.write(f"作者: {self.novel_author}\n")
            f.write("=" * 50 + "\n\n")
            
            # 写入章节内容
            for i, chapter in enumerate(self.chapters, 1):
                f.write(f"\n\n第 {i} 章: {chapter['title']}\n")
                f.write("-" * 50 + "\n")
                f.write(chapter.get('content', '[内容缺失]'))
                f.write("\n")
        
        print(f"TXT文件已保存: {filename}")

    def save_as_epub(self, filename):
        """保存为EPUB格式"""
        print(f"正在保存为EPUB格式: {filename}")
        
        # 创建EPUB书籍
        book = epub.EpubBook()
        
        # 设置元数据
        book.set_identifier('novel_' + str(int(time.time())))
        book.set_title(self.novel_title)
        if self.novel_author:
            book.add_author(self.novel_author)
        book.set_language('zh-CN')
        
        # 创建目录章节
        toc_items = []
        spine = ['nav']
        
        # 添加每个章节
        for i, chapter in enumerate(self.chapters):
            chapter_title = chapter['title']
            chapter_content = chapter.get('content', '[内容缺失]')
            
            # 创建章节
            chapter_file = epub.EpubHtml(
                title=chapter_title,
                file_name=f'chapter_{i+1}.xhtml',
                lang='zh-CN'
            )
            
            # 格式化章节内容
            content_html = f"""
            <html>
            <head>
                <title>{chapter_title}</title>
                <style>
                    body {{
                        font-family: "Microsoft YaHei", "SimSun", serif;
                        line-height: 1.8;
                        padding: 1em;
                        text-align: justify;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 1.5em;
                        margin-bottom: 1em;
                    }}
                    p {{
                        text-indent: 2em;
                        margin: 0.5em 0;
                    }}
                </style>
            </head>
            <body>
                <h1>{chapter_title}</h1>
                <div>
            """
            
            # 将文本内容转换为段落
            paragraphs = chapter_content.split('\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    content_html += f"<p>{para}</p>\n"
            
            content_html += """
                </div>
            </body>
            </html>
            """
            
            chapter_file.content = content_html
            book.add_item(chapter_file)
            toc_items.append(chapter_file)
            spine.append(chapter_file)
        
        # 设置目录
        book.toc = tuple(toc_items)
        
        # 添加导航文件
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 设置spine
        book.spine = spine
        
        # 保存文件
        epub.write_epub(filename, book, {})
        print(f"EPUB文件已保存: {filename}")


def main():
    parser = argparse.ArgumentParser(description='小说下载器 - 支持下载小说并转换为EPUB或TXT格式')
    parser.add_argument('url', help='小说主页URL')
    parser.add_argument('-f', '--format', choices=['epub', 'txt', 'both'], default='both',
                       help='输出格式: epub, txt, 或 both (默认: both)')
    parser.add_argument('-o', '--output', help='输出文件名（不含扩展名）')
    
    args = parser.parse_args()
    
    downloader = NovelDownloader(args.url)
    
    # 解析章节列表
    if not downloader.parse_chapter_list():
        print("无法获取章节列表，请检查URL是否正确")
        return
    
    # 边导航边下载所有章节（按真实顺序）
    downloader.navigate_and_download_all()
    
    # 确定输出文件名
    if args.output:
        base_name = args.output
    else:
        base_name = downloader.novel_title or 'novel'
        # 清理文件名中的非法字符
        base_name = re.sub(r'[<>:"/\\|?*]', '', base_name)
    
    # 保存文件
    if args.format in ['txt', 'both']:
        txt_filename = f"{base_name}.txt"
        downloader.save_as_txt(txt_filename)
    
    if args.format in ['epub', 'both']:
        epub_filename = f"{base_name}.epub"
        downloader.save_as_epub(epub_filename)
    
    print("\n下载完成！")


if __name__ == '__main__':
    main()

