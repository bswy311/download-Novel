#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说下载器可视化界面
"""

import threading
import time
import traceback
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from novel_downloader import NovelDownloader


class GuiNovelDownloader(NovelDownloader):
    def __init__(self, base_url, status_callback=None, stop_event=None, pause_event=None):
        super().__init__(base_url)
        self.status_callback = status_callback
        self.stop_event = stop_event or threading.Event()
        self.pause_event = pause_event or threading.Event()

    def _status(self, message):
        if self.status_callback:
            self.status_callback(message)

    def request_stop(self):
        self.stop_event.set()
        self.pause_event.clear()  # 唤醒等待

    def pause_requested(self):
        return self.pause_event.is_set()

    def stop_requested(self):
        return self.stop_event.is_set()

    def parse_chapter_list(self):
        if self.stop_requested():
            self._status('已取消章节列表解析')
            return False

        self._status('正在获取章节列表...')
        success = super().parse_chapter_list()
        if self.stop_requested():
            self._status('已取消章节列表解析')
            return False

        if success:
            self._status(f'已获取章节列表，共 {len(self.chapters)} 章')
        else:
            self._status('获取章节列表失败')
        return success

    def navigate_and_download_all(self, on_pause_save=None):
        self._status('开始边导航边下载...')
        def on_chapter(index, title):
            self._status(f'正在下载第 {index} 章: {title}')
        super().navigate_and_download_all(
            progress_callback=on_chapter,
            stop_check=self.stop_requested,
            pause_check=self.pause_requested,
            pause_save_callback=on_pause_save,
        )
        if self.stop_requested():
            self._status('下载被用户终止')



class NovelDownloaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('小说下载器')
        self.geometry('660x520')
        self.resizable(False, False)

        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value='both')
        self.output_var = tk.StringVar()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        self._build_ui()
        self.download_thread = None
        self._output_file = None  # 跟踪输出文件以便终止时删除

    def _build_ui(self):
        padding = {'padx': 12, 'pady': 8}

        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, **padding)

        ttk.Label(frame, text='小说主页 URL:').grid(row=0, column=0, sticky=tk.W)
        url_entry = ttk.Entry(frame, textvariable=self.url_var, width=72)
        url_entry.grid(row=0, column=1, sticky=tk.W, columnspan=3)

        ttk.Label(frame, text='输出格式:').grid(row=1, column=0, sticky=tk.W)
        formats = [('EPUB', 'epub'), ('TXT', 'txt'), ('EPUB+TXT', 'both')]
        for idx, (label, value) in enumerate(formats):
            ttk.Radiobutton(frame, text=label, variable=self.format_var, value=value).grid(row=1, column=idx+1, sticky=tk.W)

        ttk.Label(frame, text='输出文件名（可选）:').grid(row=2, column=0, sticky=tk.W)
        output_entry = ttk.Entry(frame, textvariable=self.output_var, width=40)
        output_entry.grid(row=2, column=1, sticky=tk.W, columnspan=2)

        ttk.Label(frame, text='操作:').grid(row=3, column=0, sticky=tk.W)
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=1, columnspan=3, sticky=tk.W)

        self.start_button = ttk.Button(btn_frame, text='开始下载', command=self.start_download)
        self.start_button.pack(side=tk.LEFT, padx=(0, 4))

        self.pause_button = ttk.Button(btn_frame, text='暂停下载', command=self.pause_download, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=4)

        self.resume_button = ttk.Button(btn_frame, text='继续下载', command=self.resume_download, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=4)

        self.stop_button = ttk.Button(btn_frame, text='终止下载', command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=4)

        ttk.Separator(frame, orient='horizontal').grid(row=4, column=0, columnspan=5, sticky='ew', pady=10)

        ttk.Label(frame, text='日志与状态:').grid(row=5, column=0, sticky=tk.W)
        self.log_text = tk.Text(frame, width=78, height=20, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=6, column=0, columnspan=4, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=6, column=4, sticky='ns')
        self.log_text['yscrollcommand'] = scrollbar.set

        frame.grid_rowconfigure(6, weight=1)

    def append_log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def set_controls_state(self, state):
        """state: 'idle', 'running', 'paused'"""
        self.start_button.configure(state=tk.NORMAL if state == 'idle' else tk.DISABLED)
        self.pause_button.configure(state=tk.NORMAL if state == 'running' else tk.DISABLED)
        self.resume_button.configure(state=tk.NORMAL if state == 'paused' else tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL if state in ('running', 'paused') else tk.DISABLED)

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning('输入错误', '请输入小说主页 URL。')
            return

        self.stop_event.clear()
        self.pause_event.clear()
        self._output_file = None
        self.set_controls_state('running')
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state=tk.DISABLED)

        self.download_thread = threading.Thread(target=self._download_worker, args=(url,), daemon=True)
        self.download_thread.start()

    def _download_worker(self, url):
        output_name = self.output_var.get().strip() or None
        format_choice = self.format_var.get()

        downloader = GuiNovelDownloader(
            url,
            status_callback=self._thread_safe_status,
            stop_event=self.stop_event,
            pause_event=self.pause_event,
        )

        try:
            self._thread_safe_status('开始解析章节列表...')
            if not downloader.parse_chapter_list():
                self._thread_safe_status('下载失败：无法解析章节列表，请检查 URL 或网络。')
                self._thread_safe_finish(False, '章节解析失败')
                return

            if len(downloader.chapters) == 0:
                self._thread_safe_status('下载失败：未找到任何章节链接。')
                self._thread_safe_finish(False, '未找到章节')
                return

            base_name = output_name or downloader.novel_title or 'novel'
            base_name = self._sanitize_filename(base_name)

            # 暂停时保存已下载内容
            def on_pause_save(downloaded):
                self._thread_safe_status(f'暂停保存: 已下载 {downloaded} 章')
                txt_filename = f'{base_name}_partial.txt'
                downloader.save_as_txt(txt_filename)
                self._thread_safe_status(f'暂停保存成功: {txt_filename}')
                self._output_file = txt_filename

            self._thread_safe_status('开始下载（边导航边下载）...')
            downloader.navigate_and_download_all(on_pause_save=on_pause_save)

            if downloader.stop_requested():
                # 终止下载：删除未完成的文件
                if self._output_file and os.path.exists(self._output_file):
                    try:
                        os.remove(self._output_file)
                        self._thread_safe_status(f'已删除未完成文件: {self._output_file}')
                    except:
                        pass
                self._thread_safe_finish(False, '下载已终止')
                return

            if self.pause_event.is_set():
                self._thread_safe_finish(True, f'下载已暂停，已保存到 {self._output_file or base_name}')
                return

            # 正常完成：保存最终文件
            self._thread_safe_status('正在保存文件...')

            if format_choice in ['txt', 'both']:
                txt_filename = f'{base_name}.txt'
                downloader.save_as_txt(txt_filename)
                self._thread_safe_status(f'TXT 保存成功: {txt_filename}')

            if format_choice in ['epub', 'both']:
                epub_filename = f'{base_name}.epub'
                downloader.save_as_epub(epub_filename)
                self._thread_safe_status(f'EPUB 保存成功: {epub_filename}')

            # 删除暂停时留下的临时文件
            partial_file = f'{base_name}_partial.txt'
            if os.path.exists(partial_file):
                try:
                    os.remove(partial_file)
                    self._thread_safe_status(f'已删除临时文件: {partial_file}')
                except:
                    pass

            self._thread_safe_finish(True, '下载完成')
        except Exception as error:
            error_message = ''.join(traceback.format_exception_only(type(error), error)).strip()
            self._thread_safe_status(f'下载失败：{error_message}')
            self._thread_safe_finish(False, error_message)

    def _sanitize_filename(self, name):
        return ''.join(ch for ch in name if ch not in '<>:"/\\|?*').strip() or 'novel'

    def _thread_safe_status(self, message):
        self.after(0, lambda: self._update_status(message))

    def _thread_safe_finish(self, success, message):
        self.after(0, lambda: self._finish_download(success, message))

    def pause_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.pause_event.set()
            self.set_controls_state('paused')
            self._thread_safe_status('暂停请求已发送，等待当前章节完成后暂停...')

    def resume_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.pause_event.clear()
            self.set_controls_state('running')
            self._thread_safe_status('继续下载...')

    def stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.stop_event.set()
            self.pause_event.clear()
            self._thread_safe_status('终止请求已发送，正在清理...')

    def _update_status(self, message):
        self.append_log(message)

    def _finish_download(self, success, message):
        self.set_controls_state('idle')
        if success:
            messagebox.showinfo('下载结果', message)
        else:
            messagebox.showwarning('下载结果', message)


if __name__ == '__main__':
    app = NovelDownloaderGUI()
    app.mainloop()
