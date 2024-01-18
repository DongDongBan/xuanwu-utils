import tkinter as tk
import tkinter.ttk as ttk
import json
from datetime import datetime

class JSONViewer(tk.Toplevel):
    def __init__(self, json_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("详细信息")
        self.geometry("600x900")

        # Create a frame for tree and scrollbars
        frame = ttk.Frame(self)
        frame.pack(expand=True, fill=tk.BOTH)

        # Create the treeview
        self.tree = ttk.Treeview(frame)
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # Create the vertical scrollbar
        v_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        v_scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        # Create buttons
        expand_button = ttk.Button(self, text="展开所有", command=self.expand_all)
        expand_button.pack(side='left')
        collapse_button = ttk.Button(self, text="折叠所有", command=self.collapse_all)
        collapse_button.pack(side='right')

        # Populate the treeview with JSON data
        self.insert_json('', json_data)
   

    # def insert_json(self, parent, json_data):
    #     if isinstance(json_data, dict):
    #         for key, value in json_data.items():
    #             new_parent = self.tree.insert(parent, 'end', text=key)
    #             self.insert_json(new_parent, value)
    #     elif isinstance(json_data, list):
    #         for i, value in enumerate(json_data):
    #             new_parent = self.tree.insert(parent, 'end', text=str(i))
    #             self.insert_json(new_parent, value)
    #     else:
    #         self.tree.insert(parent, 'end', text=str(json_data))

    def insert_json(self, parent, json_data):
        if isinstance(json_data, dict):
            for key, value in json_data.items():
                new_parent = self.tree.insert(parent, 'end', text=key)
                self.insert_json(new_parent, value)
        elif isinstance(json_data, list):
            for i, value in enumerate(json_data):
                new_parent = self.tree.insert(parent, 'end', text=str(i))
                self.insert_json(new_parent, value)
        elif isinstance(json_data, datetime):
            formatted_date = json_data.isoformat()
            self.tree.insert(parent, 'end', text=formatted_date)
        else:
            if json_data is True:
                value = 'True'
            elif json_data is False:
                value = 'False'
            else:
                value = str(json_data)
            self.tree.insert(parent, 'end', text=value)    

    def expand_all(self):
        for item in self.tree.get_children(''):
            self.expand_subtree(item)

    def expand_subtree(self, item):
        self.tree.item(item, open=True)
        for child in self.tree.get_children(item):
            self.expand_subtree(child)

    def collapse_all(self):
        for item in self.tree.get_children(''):
            self.tree.item(item, open=False)