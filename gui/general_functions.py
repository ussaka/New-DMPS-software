"""
General function for the ui classes
"""

import tkinter as tk
from tkinter import ttk, messagebox

import config


def create_labels(container: ttk.LabelFrame or tk.Menu, names: list, row_num: int, col_num: int, pos: str,
                  row_offset: int) -> list:
    """
    Create labels from given list of names and other parameters

    Return list of created label objects
    """

    labels_list = []
    for name in names:
        label = ttk.Label(container, text=name)
        label.grid(row=row_num, column=col_num, sticky=pos, padx=5, pady=5)
        row_num += row_offset
        labels_list.append(label)

    return labels_list


def create_entries(container: ttk.LabelFrame or tk.Menu, items: dict, row_num: int, col_num: int, pos: str,
                   row_offset: int) -> dict:
    """
    Create entries from given dict

    Returns dict of created entries
    """

    entries = {}
    for item in items:
        entry = tk.Entry(container, width=7)  # Create entry
        entry.insert(tk.END, items.get(item))  # Insert value from the item to the entry field
        entries[item] = entry  # Add entry to the entries dict
        entry.grid(row=row_num, column=col_num, sticky=pos, padx=5, pady=5)
        row_num += row_offset

    return entries


def save_entries(entries: dict, conf: config.Config, section: str) -> None:
    """
    Write values from entries to the ini file
    """

    for name in entries:
        # Update value in the ini file
        conf.write(section, name, entries[name].get())

    messagebox.showinfo(message="Saved!")  # Display message
