import sys
import os
import json
import subprocess
import threading
import platform
import importlib.util
import webbrowser
import traceback
from datetime import datetime

from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QTimer, QMimeData
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                            QPushButton, QLineEdit, QTextEdit, QTreeWidget, 
                            QTreeWidgetItem, QGroupBox, QStatusBar, QCheckBox, 
                            QMessageBox, QSplitter, QFrame, QStyle, QProgressDialog,
                            QComboBox, QApplication)
from PyQt6.QtGui import QFont, QIcon, QAction, QClipboard

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    print("QtWebEngine not available. Will use system browser instead.")
    WEB_ENGINE_AVAILABLE = False

MODEL_CATEGORIES = {
    "Vision": ["vision", "image", "visual", "multimodal", "llava", "bakllava", "v-", "-v"],
    "Coding": ["code", "coder", "coding", "programming", "developer", "codellama", "starcoder"],
    "Math": ["math", "mathematics", "calculation", "reasoning"],
    "Tools": ["tool", "function", "api", "call", "tool-use"],
    "Medical": ["medical", "healthcare", "medicine", "meditron", "medllama"],
    "Uncensored": ["uncensored", "unfiltered"],
    "Reasoning": ["reasoning", "logic", "thinker", "deepthought", "reflect"],
    "Embed": ["embed", "embedding", "vector"]
}

class DownloadThread(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, int)
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        
    def run(self):
        try:
            process = subprocess.Popen(
                self.command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=1
            )
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                    
                try:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    self.progress_signal.emit(decoded_line)
                except Exception as e:
                    self.progress_signal.emit(f"Warning: Could not decode output line: {e}")
            
            process.wait()
            self.finished_signal.emit(process.returncode == 0, process.returncode)
                
        except Exception as e:
            self.progress_signal.emit(f"Error during download: {e}")
            self.finished_signal.emit(False, -1)

class ScraperThread(QThread):
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, scrape_file):
        super().__init__()
        self.scrape_file = scrape_file
        
    def run(self):
        try:
            spec = importlib.util.spec_from_file_location("scrape", self.scrape_file)
            scrape_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scrape_module)
            
            scrape_module.scrape_ollama_models()
            self.finished_signal.emit(True, "")
            
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class OllamaModelManager(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setWindowTitle("Ollama Model Manager")
            self.resize(1000, 700)
            
            self.json_file = os.path.join(os.path.dirname(__file__), "ollama_models.json")
            self.scrape_file = os.path.join(os.path.dirname(__file__), "scrape.py")
            
            self.browser_mode = "Embedded QtWebEngine" if WEB_ENGINE_AVAILABLE else "System Default Browser"
            
            self.models = []
            self.current_model_url = ""
            
            self.setup_ui()
            
            self.load_models()
            
            self.refresh_downloaded_models()
        
        except Exception as e:
            self.show_error_and_exit("Error initializing application", str(e))

    def show_error_and_exit(self, title, error_message):
        try:
            error_details = f"{error_message}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, title, error_details)
            sys.exit(1)
        except:
            print(f"FATAL ERROR: {title} - {error_message}")
            sys.exit(1)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        self.browse_tab = QWidget()
        self.tab_widget.addTab(self.browse_tab, "Browse Models")
        
        self.downloaded_tab = QWidget()
        self.tab_widget.addTab(self.downloaded_tab, "Downloaded Models")
        
        if WEB_ENGINE_AVAILABLE:
            self.browser_tab = QWidget()
            self.tab_widget.addTab(self.browser_tab, "Model Info")
            self.setup_browser_tab()
        
        self.setup_browse_tab()
        
        self.setup_downloaded_tab()
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(f"Browser Mode: {self.browser_mode}")

    def setup_browse_tab(self):
        try:
            browse_layout = QVBoxLayout(self.browse_tab)
            
            control_layout = QHBoxLayout()
            browse_layout.addLayout(control_layout)
            
            control_layout.addWidget(QLabel("Search:"))
            self.search_input = QLineEdit()
            self.search_input.setMinimumWidth(300)
            self.search_input.textChanged.connect(self.filter_models)
            control_layout.addWidget(self.search_input)
            
            control_layout.addStretch(1)
            
            reset_btn = QPushButton("Reset Filters")
            reset_btn.clicked.connect(self.reset_filters)
            control_layout.addWidget(reset_btn)
            
            update_btn = QPushButton("Update Models List")
            update_btn.clicked.connect(self.update_models)
            control_layout.addWidget(update_btn)
            
            filter_group = QGroupBox("Filter Models by Category")
            browse_layout.addWidget(filter_group)
            
            filter_layout = QGridLayout(filter_group)
            
            self.category_checkboxes = {}
            row, col = 0, 0
            max_cols = 4
            
            for category in MODEL_CATEGORIES.keys():
                checkbox = QCheckBox(category)
                checkbox.stateChanged.connect(self.filter_models)
                filter_layout.addWidget(checkbox, row, col)
                self.category_checkboxes[category] = checkbox
                
                col += 1
                if col >= max_cols:
                    row += 1
                    col = 0
            
            splitter = QSplitter(Qt.Orientation.Vertical)
            browse_layout.addWidget(splitter, 1)
            
            models_widget = QWidget()
            models_layout = QVBoxLayout(models_widget)
            models_layout.setContentsMargins(0, 0, 0, 0)
            
            self.models_tree = QTreeWidget()
            self.models_tree.setHeaderLabels(["Name", "Description", "Categories"])
            self.models_tree.setColumnWidth(0, 150)
            self.models_tree.setColumnWidth(1, 500)
            self.models_tree.setColumnWidth(2, 150)
            self.models_tree.itemSelectionChanged.connect(self.on_model_select)
            self.models_tree.setAlternatingRowColors(True)
            models_layout.addWidget(self.models_tree)
            
            splitter.addWidget(models_widget)
            
            download_widget = QWidget()
            download_layout = QVBoxLayout(download_widget)
            
            info_group = QGroupBox("Download Model")
            download_layout.addWidget(info_group)
            info_layout = QGridLayout(info_group)
            
            info_layout.addWidget(QLabel("Selected Model:"), 0, 0)
            self.selected_model_label = QLabel("")
            info_layout.addWidget(self.selected_model_label, 0, 1)
            
            info_layout.addWidget(QLabel("Variant:"), 1, 0)
            self.variant_combo = QComboBox()
            self.variant_combo.currentIndexChanged.connect(self.update_command_text)
            info_layout.addWidget(self.variant_combo, 1, 1)
            
            info_layout.addWidget(QLabel("Command:"), 2, 0)
            
            cmd_layout = QHBoxLayout()
            info_layout.addLayout(cmd_layout, 2, 1)
            
            self.command_text = QTextEdit()
            self.command_text.setMaximumHeight(80)
            cmd_layout.addWidget(self.command_text)
            
            copy_btn = QPushButton()
            copy_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
            copy_btn.setToolTip("Copy command to clipboard")
            copy_btn.clicked.connect(self.copy_command_to_clipboard)
            copy_btn.setFixedWidth(40)
            cmd_layout.addWidget(copy_btn)
            
            button_layout = QHBoxLayout()
            info_layout.addLayout(button_layout, 3, 1)
            
            self.download_btn = QPushButton("Download")
            self.download_btn.setEnabled(False)
            self.download_btn.clicked.connect(self.download_model)
            button_layout.addWidget(self.download_btn)
            
            view_btn = QPushButton("View Model Page")
            view_btn.clicked.connect(self.view_model_page)
            button_layout.addWidget(view_btn)
            button_layout.addStretch(1)
            
            progress_group = QGroupBox("Download Progress")
            download_layout.addWidget(progress_group, 1)
            progress_layout = QVBoxLayout(progress_group)
            
            self.progress_text = QTextEdit()
            self.progress_text.setReadOnly(True)
            progress_layout.addWidget(self.progress_text)
            
            splitter.addWidget(download_widget)
            
            splitter.setSizes([400, 300])
            
        except Exception as e:
            self.show_error_and_exit("Failed to set up browse tab", str(e))

    def setup_downloaded_tab(self):
        try:
            downloaded_layout = QVBoxLayout(self.downloaded_tab)
            
            control_layout = QHBoxLayout()
            downloaded_layout.addLayout(control_layout)
            
            delete_btn = QPushButton("Delete Selected")
            delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
            delete_btn.clicked.connect(self.delete_selected_model)
            control_layout.addWidget(delete_btn)
            
            control_layout.addStretch(1)
            
            refresh_btn = QPushButton("Refresh List")
            refresh_btn.clicked.connect(self.refresh_downloaded_models)
            control_layout.addWidget(refresh_btn)
            
            self.downloaded_tree = QTreeWidget()
            self.downloaded_tree.setHeaderLabels(["Name", "Size", "Modified"])
            self.downloaded_tree.setColumnWidth(0, 300)
            self.downloaded_tree.setColumnWidth(1, 100)
            self.downloaded_tree.setColumnWidth(2, 200)
            self.downloaded_tree.setAlternatingRowColors(True)
            self.downloaded_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
            downloaded_layout.addWidget(self.downloaded_tree)
        
        except Exception as e:
            self.show_error_and_exit("Failed to set up downloaded tab", str(e))

    def setup_browser_tab(self):
        if WEB_ENGINE_AVAILABLE:
            try:
                browser_layout = QVBoxLayout(self.browser_tab)
                browser_layout.setContentsMargins(0, 0, 0, 0)
                
                status_layout = QHBoxLayout()
                browser_layout.addLayout(status_layout)
                
                self.browser_status_label = QLabel("Loading... Commands will be extracted automatically")
                status_layout.addWidget(self.browser_status_label)
                status_layout.addStretch(1)
                
                self.web_view = QWebEngineView()
                browser_layout.addWidget(self.web_view)
                
                self.web_view.setUrl(QUrl("about:blank"))
                
                self.web_view.loadFinished.connect(self.on_page_load_finished)
                
            except Exception as e:
                print(f"Error setting up browser tab: {e}")
                self.browser_mode = "System Default Browser"

    def load_models(self):
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                self.models = json.load(f)
            self.populate_models_tree(self.models)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load models: {e}\nThe models list will be empty.")
            self.models = []

    def populate_models_tree(self, models):
        try:
            self.models_tree.clear()
            
            for model in models:
                categories = self.categorize_model(model)
                categories_str = ", ".join(categories)
                
                item = QTreeWidgetItem(self.models_tree)
                item.setText(0, model["name"])
                item.setText(1, model["description"])
                item.setText(2, categories_str)
                
                item.setData(0, Qt.ItemDataRole.UserRole, model)
                
            self.models_tree.resizeColumnToContents(0)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to populate models: {e}")

    def filter_models(self):
        try:
            search_term = self.search_input.text().lower()
            
            selected_categories = [cat for cat, checkbox in self.category_checkboxes.items() 
                                  if checkbox.isChecked()]
            
            filtered_models = []
            
            for model in self.models:
                if search_term and not (search_term in model["name"].lower() or 
                                        search_term in model["description"].lower()):
                    continue
                
                if selected_categories:
                    model_categories = self.categorize_model(model)
                    
                    if not any(cat in selected_categories for cat in model_categories):
                        continue
                
                filtered_models.append(model)
            
            self.populate_models_tree(filtered_models)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error filtering models: {e}")

    def categorize_model(self, model):
        try:
            categories = []
            model_text = (model["name"] + " " + model["description"]).lower()
            
            for category, keywords in MODEL_CATEGORIES.items():
                for keyword in keywords:
                    if keyword.lower() in model_text:
                        categories.append(category)
                        break
                        
            return categories
        except Exception as e:
            print(f"Error categorizing model {model.get('name', 'unknown')}: {e}")
            return []

    def reset_filters(self):
        try:
            self.search_input.clear()
            for checkbox in self.category_checkboxes.values():
                checkbox.setChecked(False)
            self.filter_models()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to reset filters: {e}")

    def on_model_select(self):
        try:
            selected_items = self.models_tree.selectedItems()
            if not selected_items:
                return
                
            item = selected_items[0]
            model_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if model_data:
                model_name = model_data["name"]
                self.selected_model_label.setText(model_name)
                
                self.current_base_model = model_name
                
                self.extracted_commands = []
                
                self.variant_combo.clear()
                self.variant_combo.addItem("Loading variants...", "")
                
                self.command_text.setText(f"ollama pull {model_name}")
                
                self.download_btn.setEnabled(True)
                
                self.current_model_url = model_data["url"]
                
                if WEB_ENGINE_AVAILABLE and self.current_model_url:
                    self.web_view.setUrl(QUrl(self.current_model_url))
                    self.statusBar.showMessage(f"Loading variants for {model_name}...", 3000)
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error selecting model: {e}")
    
    def update_variant_options(self, extracted_variants=None):
        try:
            self.variant_combo.clear()
            
            self.variant_combo.addItem("default", "")
            
            if extracted_variants:
                for variant in extracted_variants:
                    if ':' in variant:
                        model_name, tag = variant.split(':', 1)
                        if model_name == self.current_base_model:
                            self.variant_combo.addItem(f"{tag}", variant)
                        else:
                            self.variant_combo.addItem(f"{variant}", variant)
                    else:
                        self.variant_combo.addItem(f"{variant}", variant)
            
            self.variant_combo.addItem("Custom...", "custom")
            
            self.update_command_text()
            
        except Exception as e:
            print(f"Error updating variant options: {e}")

    def update_command_text(self):
        try:
            model_name = self.selected_model_label.text()
            if not model_name:
                return
                
            variant_data = self.variant_combo.currentData()
            
            if variant_data == "custom":
                self.command_text.clear()
                self.command_text.setPlaceholderText("Enter custom command (e.g., ollama pull model:tag)")
            else:
                if hasattr(self, 'extracted_commands') and self.extracted_commands:
                    for cmd in self.extracted_commands:
                        if cmd['modelSpec'] == variant_data:
                            self.command_text.setText(f"ollama pull {cmd['modelSpec']}")
                            return
                
                cmd = f"ollama pull {model_name}"
                if variant_data and variant_data != model_name and variant_data != "":
                    if ':' in variant_data:
                        cmd = f"ollama pull {variant_data}"
                    else:
                        cmd += f":{variant_data}"
                    
                self.command_text.setText(cmd)
                
        except Exception as e:
            print(f"Error updating command text: {e}")

    def copy_command_to_clipboard(self):
        try:
            command = self.command_text.toPlainText().strip()
            if command:
                clipboard = QApplication.clipboard()
                clipboard.setText(command)
                
                self.statusBar.showMessage("Command copied to clipboard", 3000)
        except Exception as e:
            print(f"Error copying to clipboard: {e}")

    def download_model(self):
        try:
            model_name = self.selected_model_label.text()
            
            if not model_name:
                return
            
            cmd = self.command_text.toPlainText().strip()
            if not cmd:
                QMessageBox.warning(self, "Error", "Please enter a command to download the model.")
                return
            
            self.progress_text.clear()
            
            self.log_progress(f"Starting download: {cmd}")
            
            self.download_btn.setEnabled(False)
            
            self.download_thread = DownloadThread(cmd)
            self.download_thread.progress_signal.connect(self.log_progress)
            self.download_thread.finished_signal.connect(self.on_download_finished)
            self.download_thread.start()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error starting download: {e}")
            self.download_btn.setEnabled(True)

    def on_download_finished(self, success, return_code):
        try:
            if (success):
                self.log_progress("Download completed successfully!")
                self.tab_widget.setCurrentIndex(1)
                self.refresh_downloaded_models()
            else:
                self.log_progress(f"Download failed with return code: {return_code}")
                
            self.download_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error handling download completion: {e}")
            self.download_btn.setEnabled(True)

    def log_progress(self, message):
        try:
            self.progress_text.append(message)
            cursor = self.progress_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.progress_text.setTextCursor(cursor)
        except Exception as e:
            print(f"Error logging progress: {e}")

    def refresh_downloaded_models(self):
        try:
            self.downloaded_tree.clear()
            
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True,
                check=True
            )
            
            lines = result.stdout.strip().split('\n')
            if lines and len(lines) > 1:
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        size = parts[1]
                        modified = " ".join(parts[2:])
                        
                        item = QTreeWidgetItem(self.downloaded_tree)
                        item.setText(0, name)
                        item.setText(1, size)
                        item.setText(2, modified)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not get downloaded models: {e}")

    def update_models(self):
        try:
            QMessageBox.information(self, "Update Models", 
                                   "Updating models list from Ollama website. This may take a while.")
            
            self.scraper_thread = ScraperThread(self.scrape_file)
            self.scraper_thread.finished_signal.connect(self.on_update_finished)
            self.scraper_thread.start()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error starting update: {e}")

    def on_update_finished(self, success, error_message):
        try:
            if success:
                QMessageBox.information(self, "Update Complete", 
                                       "Models list has been updated successfully!")
                self.load_models()
            else:
                QMessageBox.warning(self, "Update Error", 
                                   f"Failed to update models: {error_message}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error handling update completion: {e}")

    def view_model_page(self):
        try:
            model_name = self.selected_model_label.text()
            if not model_name:
                QMessageBox.information(self, "Info", "Please select a model first")
                return
            
            selected_model = next((m for m in self.models if m["name"] == model_name), None)
            
            if selected_model and selected_model.get("url"):
                url = selected_model["url"]
                
                if WEB_ENGINE_AVAILABLE:
                    self.tab_widget.setCurrentIndex(2)
                    self.statusBar.showMessage(f"Viewing {model_name} page", 3000)
                else:
                    webbrowser.open(url)
                    
                    QMessageBox.information(
                        self, 
                        "Model Page",
                        "The model page has been opened in your default browser. "
                        "Look for 'ollama run' commands and replace 'run' with 'pull' to download the model."
                    )
            else:
                QMessageBox.information(self, "Info", "No URL available for this model")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error viewing model page: {e}")

    def on_page_load_finished(self, success):
        if success:
            model_name = self.selected_model_label.text()
            self.browser_status_label.setText(f"Extracting variants for {model_name}...")
            self.extract_commands_from_page()

    def extract_commands_from_page(self):
        if not WEB_ENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
            
        script = """
        (function() {
            var elements = document.querySelectorAll('code, pre, div.copy-text, button[data-clipboard-text], span, p, div');
            var commands = [];
            var modelVariants = [];
            
            for (var i = 0; i < elements.length; i++) {
                var el = elements[i];
                var text = '';
                
                if (el.hasAttribute && el.hasAttribute('data-clipboard-text')) {
                    text = el.getAttribute('data-clipboard-text');
                } else {
                    text = el.textContent || el.innerText || '';
                }
                
                if (text && text.includes('ollama run ')) {
                    var commandMatch = text.match(/ollama\\s+run\\s+([\\w\\-\\.:]+)/);
                    if (commandMatch && commandMatch[1]) {
                        var modelSpec = commandMatch[1];
                        commands.push({
                            fullCommand: 'ollama run ' + modelSpec,
                            modelSpec: modelSpec
                        });
                    }
                }
            }
            
            return commands;
        })();
        """
        
        self.web_view.page().runJavaScript(script, self.process_extracted_commands)

    def process_extracted_commands(self, results):
        if not results or len(results) == 0:
            self.browser_status_label.setText("No variants found for this model.")
            self.update_variant_options([])
            return
            
        try:
            self.extracted_commands = results
            extracted_variants = []
            
            for cmd in results:
                model_spec = cmd['modelSpec']
                if (model_spec not in extracted_variants) and (self.current_base_model in model_spec):
                    extracted_variants.append(model_spec)
            
            if extracted_variants:
                self.browser_status_label.setText("Variants loaded successfully.")
            else:
                self.browser_status_label.setText("No matching variants found for this model.")
            
            self.update_variant_options(extracted_variants)
            
            self.statusBar.showMessage(f"Variants loaded for {self.current_base_model}", 3000)
            
        except Exception as e:
            print(f"Error processing extracted commands: {e}")
            self.browser_status_label.setText(f"Error loading variants: {e}")
            self.update_variant_options([])

    def delete_selected_model(self):
        try:
            selected_items = self.downloaded_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Select Model", 
                                      "Please select a model to delete")
                return
                
            model_name = selected_items[0].text(0)
            
            confirm = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the model '{model_name}'?\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                cmd = f"ollama rm {model_name}"
                
                progress_dialog = QProgressDialog("Deleting model...", "Cancel", 0, 0, self)
                progress_dialog.setWindowTitle("Deleting Model")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.show()
                
                try:
                    result = subprocess.run(
                        cmd, 
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    progress_dialog.close()
                    
                    QMessageBox.information(self, "Success", f"Model '{model_name}' was deleted successfully")
                    
                    self.refresh_downloaded_models()
                    
                except subprocess.CalledProcessError as e:
                    progress_dialog.close()
                    QMessageBox.warning(
                        self, 
                        "Error", 
                        f"Failed to delete model. Error: {e.stderr}"
                    )
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error during model deletion: {e}")

    def closeEvent(self, event):
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)
    
    window = OllamaModelManager()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
