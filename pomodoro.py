"""
番茄钟 (Pomodoro Timer) — 基于 tkinter 的可视化番茄工作法计时器

功能：
- 工作 25 分钟 / 短休息 5 分钟 / 长休息 15 分钟
- 环形进度条实时显示剩余时间
- 4 个工作周期后自动长休息
- 计时结束弹窗 + 系统提示音
- 窗口置顶选项
"""

import tkinter as tk
from tkinter import messagebox
import math

# ── 常量配置 ──────────────────────────────────────────────

WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15
CYCLES_BEFORE_LONG_BREAK = 4

# 颜色主题
COLORS = {
    "work":       {"bg": "#FFF5F5", "ring": "#E74C3C", "accent": "#C0392B", "text": "#2C3E50"},
    "short_break":{"bg": "#F0FFF4", "ring": "#2ECC71", "accent": "#27AE60", "text": "#2C3E50"},
    "long_break": {"bg": "#F0F8FF", "ring": "#3498DB", "accent": "#2980B9", "text": "#2C3E50"},
}

FONT_TITLE = ("Helvetica", 16, "bold")
FONT_TIMER = ("Helvetica Neue", 48, "bold")
FONT_MODE  = ("Helvetica", 12)
FONT_BTN   = ("Helvetica", 12, "bold")
FONT_CHECK = ("Helvetica", 11)


class PomodoroTimer:
    """番茄钟主程序"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("🍅 番茄钟")
        self.window.geometry("380x520")
        self.window.resizable(False, False)
        self.window.configure(bg="#FFFFFF")

        # 状态变量
        self.state = "IDLE"        # IDLE | RUNNING | PAUSED
        self.mode = "work"         # work | short_break | long_break
        self.remaining = WORK_MIN * 60   # 剩余秒数
        self.total = WORK_MIN * 60       # 当前模式总秒数
        self.completed_cycles = 0        # 已完成工作周期数
        self._timer_id = None            # after() 回调 ID

        self._build_ui()
        self._update_display()

        # 窗口关闭回调
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI 构建 ─────────────────────────────────────────

    def _build_ui(self):
        """构建全部界面组件"""
        c = COLORS["work"]

        # 标题
        self.lbl_title = tk.Label(
            self.window, text="🍅 Pomodoro Timer", font=FONT_TITLE,
            bg="#FFFFFF", fg=c["text"]
        )
        self.lbl_title.pack(pady=(20, 10))

        # Canvas：环形进度条 + 计时文字
        self.canvas_size = 240
        self.canvas = tk.Canvas(
            self.window, width=self.canvas_size, height=self.canvas_size,
            bg="#FFFFFF", highlightthickness=0
        )
        self.canvas.pack(pady=(0, 5))

        # 模式标签
        self.lbl_mode = tk.Label(
            self.window, text="专注工作", font=FONT_MODE,
            bg="#FFFFFF", fg=c["ring"]
        )
        self.lbl_mode.pack(pady=(0, 10))

        # 按钮框架
        btn_frame = tk.Frame(self.window, bg="#FFFFFF")
        btn_frame.pack(pady=(0, 15))

        self.btn_start = tk.Button(
            btn_frame, text="▶  开始", font=FONT_BTN, width=8,
            bg=c["ring"], fg="#FFFFFF", activebackground=c["accent"],
            borderwidth=0, cursor="hand2", command=self.start
        )
        self.btn_start.pack(side="left", padx=4)

        self.btn_pause = tk.Button(
            btn_frame, text="⏸  暂停", font=FONT_BTN, width=8,
            bg="#BDC3C7", fg="#FFFFFF", activebackground="#95A5A6",
            borderwidth=0, cursor="hand2", command=self.pause, state="disabled"
        )
        self.btn_pause.pack(side="left", padx=4)

        self.btn_reset = tk.Button(
            btn_frame, text="↺  重置", font=FONT_BTN, width=8,
            bg="#95A5A6", fg="#FFFFFF", activebackground="#7F8C8D",
            borderwidth=0, cursor="hand2", command=self.reset
        )
        self.btn_reset.pack(side="left", padx=4)

        # 完成进度指示（圆点）
        self.dots_frame = tk.Frame(self.window, bg="#FFFFFF")
        self.dots_frame.pack(pady=(0, 10))
        self.lbl_dots = tk.Label(self.dots_frame, text="", font=("Helvetica", 18), bg="#FFFFFF")
        self.lbl_dots.pack(side="left")
        self.lbl_cycle = tk.Label(
            self.dots_frame, text="  周期 0", font=FONT_MODE,
            bg="#FFFFFF", fg="#7F8C8D"
        )
        self.lbl_cycle.pack(side="left")

        # 置顶复选框
        self.var_topmost = tk.BooleanVar(value=False)
        self.chk_topmost = tk.Checkbutton(
            self.window, text="窗口置顶", font=FONT_CHECK,
            variable=self.var_topmost, bg="#FFFFFF",
            activebackground="#FFFFFF", cursor="hand2",
            command=self._toggle_topmost
        )
        self.chk_topmost.pack(pady=(0, 10))

    # ── 核心逻辑 ─────────────────────────────────────────

    def start(self):
        """开始 / 继续计时"""
        if self.state == "IDLE":
            self._set_times_for_mode()
        elif self.state == "PAUSED":
            pass  # 从中断处继续

        self.state = "RUNNING"
        self._set_button_state("RUNNING")
        self._tick()

    def pause(self):
        """暂停计时"""
        if self._timer_id:
            self.window.after_cancel(self._timer_id)
            self._timer_id = None
        self.state = "PAUSED"
        self._set_button_state("PAUSED")

    def reset(self):
        """重置当前模式计时"""
        if self._timer_id:
            self.window.after_cancel(self._timer_id)
            self._timer_id = None
        self.state = "IDLE"
        self._set_times_for_mode()
        self._set_button_state("IDLE")
        self._update_display()

    def _tick(self):
        """每秒回调：更新倒计时"""
        if self.state != "RUNNING":
            return

        if self.remaining <= 0:
            self._on_finish()
            return

        self.remaining -= 1
        self._update_display()
        self._timer_id = self.window.after(1000, self._tick)

    def _on_finish(self):
        """计时结束处理"""
        self.state = "IDLE"
        self._set_button_state("IDLE")

        # 播放系统提示音
        self.window.bell()

        if self.mode == "work":
            self.completed_cycles += 1
            # 判断下一个模式
            if self.completed_cycles % CYCLES_BEFORE_LONG_BREAK == 0:
                next_mode = "long_break"
                msg = f"🎉 已完成 {self.completed_cycles} 个番茄！\n\n休息 15 分钟吧～"
            else:
                next_mode = "short_break"
                msg = f"✅ 第 {self.completed_cycles} 个番茄完成！\n\n休息 5 分钟吧～"
        else:
            next_mode = "work"
            msg = "⏰ 休息结束！\n\n开始新的番茄吧～"

        self.mode = next_mode
        self._set_times_for_mode()
        self._apply_theme()
        self._update_display()
        messagebox.showinfo("番茄钟提醒", msg)

    # ── 显示更新 ─────────────────────────────────────────

    def _update_display(self):
        """刷新 Canvas（环形进度条 + 计时文字）"""
        c = COLORS[self.mode]
        w = self.canvas_size
        r = 95          # 环形半径
        cx, cy = w // 2, w // 2  # 圆心

        self.canvas.delete("all")

        # 背景圆环（浅灰）
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=359.9, style="arc",
            outline="#EAEAEA", width=12
        )

        # 进度弧（彩色）
        progress = self.remaining / self.total if self.total > 0 else 0
        extent = 359.9 * progress
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-extent, style="arc",
            outline=c["ring"], width=12
        )

        # 中心计时文字
        mins, secs = divmod(self.remaining, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.canvas.create_text(
            cx, cy, text=time_str, font=FONT_TIMER,
            fill=c["text"], anchor="center"
        )

        # 底部进度圆点
        dots = ""
        for i in range(self.completed_cycles):
            n = i % CYCLES_BEFORE_LONG_BREAK
            if i > 0 and n == 0:
                dots += "  "
            dots += "● "
        remaining_in_set = CYCLES_BEFORE_LONG_BREAK - (self.completed_cycles % CYCLES_BEFORE_LONG_BREAK)
        if self.completed_cycles % CYCLES_BEFORE_LONG_BREAK != 0 or self.completed_cycles == 0:
            dots += "○ " * remaining_in_set
        self.lbl_dots.config(text=dots.strip())
        self.lbl_cycle.config(text=f"  周期 {self.completed_cycles}")

    def _apply_theme(self):
        """根据当前模式切换颜色主题"""
        c = COLORS[self.mode]

        mode_text = {"work": "专注工作", "short_break": "短休息", "long_break": "长休息"}
        self.lbl_mode.config(text=mode_text.get(self.mode, ""), fg=c["ring"])

        self.window.configure(bg=c["bg"])
        self.canvas.configure(bg=c["bg"])
        self.lbl_title.configure(bg=c["bg"], fg=c["text"])
        self.lbl_mode.configure(bg=c["bg"])
        self.dots_frame.configure(bg=c["bg"])
        self.lbl_dots.configure(bg=c["bg"])
        self.lbl_cycle.configure(bg=c["bg"])
        self.chk_topmost.configure(bg=c["bg"], activebackground=c["bg"])

        for btn in [self.btn_start, self.btn_pause, self.btn_reset]:
            btn.configure(bg="#FFFFFF", fg=c["text"])

        self.btn_start.configure(bg=c["ring"], fg="#FFFFFF", activebackground=c["accent"])

    def _set_times_for_mode(self):
        """设置当前模式的时长"""
        if self.mode == "work":
            self.remaining = WORK_MIN * 60
            self.total = WORK_MIN * 60
        elif self.mode == "short_break":
            self.remaining = SHORT_BREAK_MIN * 60
            self.total = SHORT_BREAK_MIN * 60
        elif self.mode == "long_break":
            self.remaining = LONG_BREAK_MIN * 60
            self.total = LONG_BREAK_MIN * 60

    def _set_button_state(self, state):
        """根据运行状态启用/禁用按钮"""
        if state == "RUNNING":
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_reset.config(state="normal")
        elif state == "PAUSED":
            self.btn_start.config(state="normal", text="▶  继续")
            self.btn_pause.config(state="disabled")
            self.btn_reset.config(state="normal")
        else:  # IDLE
            self.btn_start.config(state="normal", text="▶  开始")
            self.btn_pause.config(state="disabled")
            self.btn_reset.config(state="normal")

    def _toggle_topmost(self):
        """切换窗口置顶"""
        self.window.attributes("-topmost", self.var_topmost.get())

    def _on_close(self):
        """窗口关闭清理"""
        if self._timer_id:
            self.window.after_cancel(self._timer_id)
        self.window.destroy()

    def run(self):
        """启动主循环"""
        self.window.mainloop()


if __name__ == "__main__":
    app = PomodoroTimer()
    app.run()
