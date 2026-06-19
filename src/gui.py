#!/usr/bin/env python3
"""CustomTkinter GUI for de-itzmx patch install/remove."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import StringVar

import customtkinter as ctk

import gui_i18n as i18n
from common import detect_installed_csp_version, is_admin, run_elevated_sync
from patch_core import apply_patch, inspect_install, remove_patch
from state import load_csp_version, load_state, save_csp_version
from version import DEFAULT_VERSION, SUPPORTED_VERSIONS, payload_available


_STATUS_OK = ("#2d6a4f", "#52b788")
_STATUS_ERR = ("#9b2226", "#e5383b")
_STATUS_NEUTRAL = ("gray20", "gray70")


def _fit_window(root: ctk.CTk, main: ctk.CTkFrame) -> None:
    root.update_idletasks()
    root.update()
    root.update_idletasks()
    width = max(root.winfo_reqwidth(), main.winfo_reqwidth() + 24)
    height = max(root.winfo_reqheight(), main.winfo_reqheight() + 16)
    w = root._reverse_window_scaling(width)
    h = root._reverse_window_scaling(height)
    root.geometry(f"{w}x{h}")
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.resizable(False, False)


def run_gui() -> int:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    detected_ver, paint_dir, raw_product = detect_installed_csp_version(SUPPORTED_VERSIONS)
    saved_ver = load_csp_version(DEFAULT_VERSION)
    initial_ver = detected_ver or saved_ver

    root = ctk.CTk()
    root.withdraw()
    root.title(i18n.t("window_title"))

    selected_version = StringVar(value=initial_ver)
    busy = False

    main = ctk.CTkFrame(root, fg_color="transparent")
    main.grid(row=0, column=0, sticky="nw", padx=12, pady=8)

    ctk.CTkLabel(
        main,
        text=i18n.t("choose_csp_version"),
        font=ctk.CTkFont(size=14, weight="bold"),
    ).pack(anchor="w", pady=(0, 4))

    version_row = ctk.CTkFrame(main, fg_color="transparent")
    version_row.pack(fill="x", pady=(0, 8))

    version_combo = ctk.CTkComboBox(
        version_row,
        values=list(SUPPORTED_VERSIONS),
        variable=selected_version,
        width=120,
        state="readonly",
        command=lambda _v: on_version_change(),
    )
    version_combo.pack(side="left")

    version_hint = ctk.CTkLabel(
        version_row,
        text="",
        font=ctk.CTkFont(size=12),
        text_color="gray50",
        wraplength=240,
        justify="left",
    )
    version_hint.pack(side="left", padx=(10, 0))

    status_label = ctk.CTkLabel(
        main,
        text=i18n.t("status_checking"),
        wraplength=360,
        justify="left",
        font=ctk.CTkFont(size=15, weight="bold"),
    )
    status_label.pack(anchor="w", pady=(4, 0))

    detail_label = ctk.CTkLabel(
        main,
        text="",
        wraplength=360,
        justify="left",
        font=ctk.CTkFont(size=12),
        text_color="gray50",
    )
    detail_label.pack(anchor="w", pady=(4, 0))

    progress = ctk.CTkProgressBar(main, mode="indeterminate")

    buttons = ctk.CTkFrame(main, fg_color="transparent")
    buttons.pack(fill="x", pady=(14, 0))

    patch_btn = ctk.CTkButton(
        buttons, text=i18n.t("btn_patch"), width=120, command=lambda: do_patch()
    )
    patch_btn.pack(side="right")

    unpatch_btn = ctk.CTkButton(
        buttons,
        text=i18n.t("btn_unpatch"),
        width=90,
        fg_color="transparent",
        border_width=1,
        command=lambda: do_unpatch(),
    )
    unpatch_btn.pack(side="right", padx=(0, 8))

    close_btn = ctk.CTkButton(
        buttons,
        text=i18n.t("btn_close"),
        width=90,
        fg_color="transparent",
        border_width=1,
        command=root.destroy,
    )
    close_btn.pack(side="left")

    def set_busy(on: bool, message: str | None = None) -> None:
        nonlocal busy
        busy = on
        state = "disabled" if on else "normal"
        patch_btn.configure(state=state)
        unpatch_btn.configure(state=state)
        version_combo.configure(state="disabled" if on else "readonly")
        if on:
            progress.pack(fill="x", pady=(10, 0))
            progress.start()
            if message:
                status_label.configure(text=message, text_color=_STATUS_NEUTRAL)
                detail_label.configure(text="")
        else:
            progress.stop()
            progress.pack_forget()

    def version_blocked() -> bool:
        ver = selected_version.get()
        if detected_ver and ver != detected_ver:
            return True
        return not payload_available(ver)

    def update_version_hint() -> None:
        ver = selected_version.get()
        if detected_ver and ver != detected_ver:
            version_hint.configure(
                text=i18n.t("err_version_mismatch", selected=ver, installed=detected_ver),
                text_color=_STATUS_ERR,
            )
        elif raw_product and not detected_ver:
            version_hint.configure(
                text=i18n.t("csp_version_unknown", version=raw_product),
                text_color=_STATUS_ERR,
            )
        elif not payload_available(ver):
            version_hint.configure(
                text=i18n.t("payload_missing", version=ver),
                text_color=_STATUS_ERR,
            )
        elif detected_ver and ver == detected_ver:
            version_hint.configure(
                text=i18n.t("csp_detected", version=detected_ver),
                text_color="gray50",
            )
        else:
            version_hint.configure(text="")

    def refresh() -> None:
        if busy:
            return
        status_label.configure(text=i18n.t("status_checking"), text_color=_STATUS_NEUTRAL)
        detail_label.configure(text="")
        root.update_idletasks()

        ver = selected_version.get()
        save_csp_version(ver)
        update_version_hint()

        if paint_dir is None:
            status_label.configure(text=i18n.t("status_no_csp"), text_color=_STATUS_ERR)
            detail_label.configure(text=i18n.t("detail_no_csp"))
            patch_btn.configure(state="disabled")
            unpatch_btn.configure(state="disabled")
            return

        st = inspect_install(paint_dir)

        if detected_ver and detected_ver not in SUPPORTED_VERSIONS:
            status_label.configure(
                text=i18n.t("warn_version_unsupported", installed=detected_ver or "?"),
                text_color=_STATUS_ERR,
            )
            detail_label.configure(text=i18n.t("install_path", path=str(paint_dir)))
        elif version_blocked():
            if st.patched:
                saved = load_state()
                shown_ver = saved.get("csp_version", ver) if saved else ver
                status_label.configure(
                    text=i18n.t("status_patched", version=shown_ver), text_color=_STATUS_OK
                )
            elif st.partial:
                status_label.configure(
                    text=i18n.t("status_broken_proxy")
                    if st.broken_proxy
                    else i18n.t("status_partial", missing=", ".join(st.missing)),
                    text_color=_STATUS_ERR,
                )
                detail_label.configure(text=i18n.t("install_path", path=str(paint_dir)))
            else:
                status_label.configure(text=i18n.t("status_not_patched"), text_color=_STATUS_NEUTRAL)
                detail_label.configure(text=i18n.t("detail_not_patched"))
        elif st.patched:
            saved = load_state()
            shown_ver = saved.get("csp_version", ver) if saved else ver
            status_label.configure(
                text=i18n.t("status_patched", version=shown_ver), text_color=_STATUS_OK
            )
            detail_label.configure(text=i18n.t("detail_patched"))
        elif st.partial:
            status_label.configure(
                text=i18n.t("status_broken_proxy")
                if st.broken_proxy
                else i18n.t("status_partial", missing=", ".join(st.missing)),
                text_color=_STATUS_ERR,
            )
            detail_label.configure(text=i18n.t("install_path", path=str(paint_dir)))
        else:
            status_label.configure(text=i18n.t("status_not_patched"), text_color=_STATUS_NEUTRAL)
            detail_label.configure(text=i18n.t("detail_not_patched"))

        can_act = not version_blocked() and paint_dir is not None
        patch_btn.configure(state="normal" if can_act and not st.patched else "disabled")
        unpatch_btn.configure(
            state="normal" if can_act and (st.patched or st.partial) else "disabled"
        )

    def on_version_change() -> None:
        save_csp_version(selected_version.get())
        refresh()

    def run_elevated_action(action: str) -> tuple[int, str]:
        ver = selected_version.get()
        if paint_dir is None:
            messagebox.showerror(i18n.t("failed_title"), i18n.t("err_csp_not_found"))
            return 1, "not found"
        if version_blocked():
            messagebox.showerror(
                i18n.t("failed_title"),
                i18n.t("err_version_mismatch", selected=ver, installed=detected_ver or "?")
                if detected_ver
                else i18n.t("err_payload_missing", version=ver),
            )
            return 1, "blocked"

        if is_admin():
            try:
                if action == "patch":
                    apply_patch(paint_dir, ver)
                else:
                    remove_patch(paint_dir, ver)
                return 0, ""
            except Exception as exc:
                return 1, str(exc)

        return run_elevated_sync(["--" + action, "--csp-version", ver])

    def finish_action(action: str, rc: int, err: str) -> None:
        set_busy(False)
        if rc != 0:
            messagebox.showerror(
                i18n.t("failed_title"),
                i18n.localize_error(err or "failed", version=selected_version.get()),
            )
        else:
            messagebox.showinfo(
                i18n.t("done_title"),
                i18n.t("done_patch" if action == "patch" else "done_unpatch"),
            )
        refresh()

    def do_patch() -> None:
        if busy:
            return
        set_busy(True, i18n.t("working_patch"))

        def worker() -> None:
            rc, err = run_elevated_action("patch")
            root.after(0, lambda: finish_action("patch", rc, err))

        threading.Thread(target=worker, daemon=True).start()

    def do_unpatch() -> None:
        if busy:
            return
        set_busy(True, i18n.t("working_unpatch"))

        def worker() -> None:
            rc, err = run_elevated_action("unpatch")
            root.after(0, lambda: finish_action("unpatch", rc, err))

        threading.Thread(target=worker, daemon=True).start()

    refresh()
    root.deiconify()
    _fit_window(root, main)
    root.mainloop()
    return 0
