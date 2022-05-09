class win:
    def disable_console_quick_edit_mode():
        from ctypes import windll
        kernel32 = windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 128)