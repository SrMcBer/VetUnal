import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from PIL import Image, ImageTk  # Add this import
from src.pdf.main_processor import process_pdfs
from src.ocr.text_classifier import PageType
from src.pdf.converter import pdf_page_to_image 

class PDFApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.build_ui()

    def setup_window(self):
        """Configure main window properties"""
        self.root.title("Procesador de PDF - Herramienta de Procesamiento de Documentos")
        self.root.geometry("700x780")
        self.root.minsize(600, 500)
                # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")
        
        # Configure grid weights for responsive design
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

    def setup_variables(self):
        """Initialize tkinter variables"""
        self.control_path = tk.StringVar()
        self.main_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.start_value = tk.StringVar(value="1")
        self.processing = False
        self.correction_data = {}
        self.correction_event = None
        self.pending_changes = {}
        self.current_preview_image = None
        self.preview_photo = None
        
    def setup_styles(self):
        """Configure ttk styles for better appearance"""
        style = ttk.Style()

                # Configure colors and fonts
        style.configure('Title.TLabel', 
                        font=('Arial', 16, 'bold'),
                        foreground='#FFFFFF')
        
        style.configure('Section.TLabel',
                        font=('Arial', 10, 'bold'),
                        foreground='#FFFFFF')
        
        style.configure('Path.TLabel',
                        font=('Arial', 9),
                        foreground='#7f8c8d')
        
        style.configure('Success.TLabel',
                        font=('Arial', 9),
                        foreground='#27ae60')
        
        style.configure('Error.TLabel',
                        font=('Arial', 9),
                        foreground='#e74c3c')
        
        style.configure('Processing.TButton',
                        font=('Arial', 10, 'bold'))

    def build_ui(self):
        """Build the main user interface"""
        self.create_header()
        # self.create_main_content()
        self.create_scrollable_content()
        self.create_correction_ui() # Create the correction UI
        self.create_footer()

    def create_header(self):
        """Create application header"""
        header_frame = ttk.Frame(self.root)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_label = ttk.Label(header_frame, text="Procesador de Documentos PDF")
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                    text="Procesar y dividir documentos PDF basados en hojas de control",
                                    font=('Arial', 9),
                                    foreground='#7f8c8d')
        subtitle_label.pack(pady=(5, 0))
        
        # Separator
        ttk.Separator(header_frame, orient='horizontal').pack(fill='x', pady=(10, 0))

    def create_scrollable_content(self):
        """Create scrollable main content area"""
        # Create canvas and scrollbar for scrolling
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Configure scrollable frame
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Grid canvas and scrollbar
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind canvas resize to adjust scrollable frame width
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Bind mousewheel to canvas
        self.bind_mousewheel()
        
        # Create main content in scrollable frame
        self.create_main_content()

    def on_canvas_configure(self, event):
        """Handle canvas resize to adjust scrollable frame width"""
        # Update the scrollable frame width to match canvas width
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def bind_mousewheel(self):
        """Bind mousewheel events for scrolling"""
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        # Bind mousewheel when mouse enters canvas
        self.canvas.bind('<Enter>', bind_to_mousewheel)
        self.canvas.bind('<Leave>', unbind_from_mousewheel)

    def create_main_content(self):
        """Create main content area with input fields"""
        # Main container with padding
        main_frame = ttk.Frame(self.scrollable_frame)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Input files section
        self.create_input_section(main_frame)
        
        # Configuration section
        self.create_config_section(main_frame)
        
        # Progress section
        self.create_progress_section(main_frame)

    def create_input_section(self, parent):
        """Create file input section"""
        # Files section
        files_frame = ttk.LabelFrame(parent, text="Archivos de Entrada", padding=15)
        files_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        files_frame.grid_columnconfigure(1, weight=1)
        
        self.create_file_input(files_frame, "PDF de Control:", self.control_path, 0)
        self.create_file_input(files_frame, "PDF Principal:", self.main_path, 1)
        
        # Output section
        output_frame = ttk.LabelFrame(parent, text="Salida", padding=15)
        output_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        output_frame.grid_columnconfigure(1, weight=1)
        
        self.create_folder_input(output_frame, "Directorio de Salida:", self.output_dir, 0)

    def create_config_section(self, parent):
        """Create configuration section"""
        config_frame = ttk.LabelFrame(parent, text="Configuración", padding=15)
        config_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        config_frame.grid_columnconfigure(1, weight=1)
        
        # Start value input
        ttk.Label(config_frame, text="Valor de Inicio:").grid(
            row=0, column=0, sticky="w", padx=(0, 10))
        
        start_entry = ttk.Entry(config_frame, textvariable=self.start_value, width=15)
        start_entry.grid(row=0, column=1, sticky="w")
        
        # Add tooltip-like help text
        help_text = ttk.Label(config_frame, 
                                text="Número inicial para la secuencia de procesamiento de documentos",
                                font=('Arial', 8),
                                foreground='#95a5a6')
        help_text.grid(row=1, column=1, sticky="w", pady=(2, 0))

    def create_progress_section(self, parent):
        """Create progress tracking section"""
        progress_frame = ttk.LabelFrame(parent, text="Estado del Procesamiento", padding=15)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(progress_frame, text="Listo para procesar documentos")
        self.status_label.grid(row=1, column=0, sticky="w")
        
        # Progress details label
        self.details_label = ttk.Label(progress_frame, text="", font=('Arial', 8))
        self.details_label.grid(row=2, column=0, sticky="w", pady=(2, 0))

    def create_footer(self):
        """Create footer with action buttons"""
        self.footer_frame = ttk.Frame(self.root)
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))

        # Button frame
        button_frame = ttk.Frame(self.footer_frame)
        button_frame.pack(anchor="center")
        
        # Process button
        self.process_btn = ttk.Button(button_frame, text="Iniciar Procesamiento", 
                                        command=self.run_processing,
                                        style='Processing.TButton')
        self.process_btn.pack(side="left", padx=(0, 10))
        
        # Cancel button (initially disabled)
        self.cancel_btn = ttk.Button(button_frame, text="Cancelar", 
                                    command=self.cancel_processing,
                                    state="disabled")
        self.cancel_btn.pack(side="left", padx=(10, 0))
        
        # Clear button
        clear_btn = ttk.Button(button_frame, text="Limpiar Todo", 
                                command=self.clear_all_fields)
        clear_btn.pack(side="left", padx=(10, 0))

    def create_correction_ui(self):
        """Create the UI for correcting patient records."""
        self.correction_frame = ttk.Frame(self.root)
        self.correction_frame.grid_columnconfigure(0, weight=1)
        self.correction_frame.grid_rowconfigure(1, weight=1)
        
        # Initialize selection tracking
        self.selected_page_item = None
        self.selected_page_num = None

        # Header
        header_text = "Corrección Manual de Registros - Revisar y Corregir Problemas de Clasificación"
        ttk.Label(self.correction_frame, text=header_text, style='Title.TLabel').grid(row=0, column=0, pady=(0, 10))
        
        # Instructions label
        instructions = "Los registros con problemas están resaltados en rojo. Haga clic en cualquier página para previsualizar y editar su clasificación."
        ttk.Label(self.correction_frame, text=instructions, font=('Arial', 9), 
                foreground='#7f8c8d').grid(row=0, column=0, pady=(25, 10), sticky="w")
        
        # Create main content frame
        content_frame = ttk.Frame(self.correction_frame)
        content_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        content_frame.grid_columnconfigure(0, weight=2)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Left side: Treeview
        tree_frame = ttk.Frame(content_frame)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Treeview for records
        self.records_tree = ttk.Treeview(tree_frame, columns=("PageType", "Issues"), show="tree headings", height=15)
        self.records_tree.heading("#0", text="Registro / Página")
        self.records_tree.heading("PageType", text="Clasificación")
        self.records_tree.heading("Issues", text="Problemas")
        
        # Configure column widths
        self.records_tree.column("#0", width=250, minwidth=200)
        self.records_tree.column("PageType", width=120, minwidth=100)
        self.records_tree.column("Issues", width=300, minwidth=250)
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Grid treeview and scrollbar
        self.records_tree.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar.grid(row=0, column=1, sticky="ns")

        # Right side: Preview and editing
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=0)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(right_frame, text="Vista Previa de Página", padding=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)
        
        self.preview_label = ttk.Label(preview_frame, text="Seleccione una página para previsualizar", 
                                    font=('Arial', 10), foreground='#7f8c8d')
        self.preview_label.grid(row=0, column=0, pady=(0, 10))
        
        self.preview_canvas = tk.Canvas(preview_frame, bg='white', width=250, height=300, 
                                    highlightthickness=1, highlightcolor="#cccccc")
        self.preview_canvas.grid(row=1, column=0, sticky="nsew")
        
        # Editing controls frame
        edit_frame = ttk.LabelFrame(right_frame, text="Cambiar Clasificación", padding=10)
        edit_frame.grid(row=1, column=0, sticky="ew")
        edit_frame.grid_columnconfigure(0, weight=1)
        
        # Current type display
        self.current_type_label = ttk.Label(edit_frame, text="Seleccione una página para editar", 
                                        font=('Arial', 10, 'bold'))
        self.current_type_label.grid(row=0, column=0, pady=(0, 10))
        
        # Buttons for each page type
        from src.ocr.text_classifier import PageType
        
        # Create style for selected button
        style = ttk.Style()
        style.configure("Selected.TButton", relief="solid", borderwidth=2)
        
        button_frame = ttk.Frame(edit_frame)
        button_frame.grid(row=1, column=0, pady=(0, 10))
        
        self.type_buttons = []
        
        # Historia Clinica button
        historia_btn = ttk.Button(button_frame, text="Historia Clínica", 
                                command=lambda: self._change_page_type(PageType.HISTORIA_CLINICA),
                                state="disabled")
        historia_btn.pack(side="top", fill="x", pady=2)
        self.type_buttons.append(historia_btn)
        
        # Cedula button
        cedula_btn = ttk.Button(button_frame, text="Cédula", 
                            command=lambda: self._change_page_type(PageType.CEDULA),
                            state="disabled")
        cedula_btn.pack(side="top", fill="x", pady=2)
        self.type_buttons.append(cedula_btn)
        
        # Recibo button
        recibo_btn = ttk.Button(button_frame, text="Recibo", 
                            command=lambda: self._change_page_type(PageType.RECIBO),
                            state="disabled")
        recibo_btn.pack(side="top", fill="x", pady=2)
        self.type_buttons.append(recibo_btn)
        
        # Unknown button
        unknown_btn = ttk.Button(button_frame, text="Desconocido/Otro", 
                                command=lambda: self._change_page_type(PageType.UNKNOWN),
                                state="disabled")
        unknown_btn.pack(side="top", fill="x", pady=2)
        self.type_buttons.append(unknown_btn)
        
        # Feedback label
        self.edit_feedback_label = ttk.Label(edit_frame, text="", font=('Arial', 9))
        self.edit_feedback_label.grid(row=2, column=0, pady=(5, 0))
        
        # Bind events
        self.records_tree.bind("<Button-1>", self.on_tree_single_click)

        # Summary label
        self.summary_label = ttk.Label(self.correction_frame, text="", font=('Arial', 9))
        self.summary_label.grid(row=2, column=0, pady=(5, 10), sticky="w")

        # Action buttons
        btn_frame = ttk.Frame(self.correction_frame)
        btn_frame.grid(row=3, column=0, pady=(10, 0))

        apply_btn = ttk.Button(btn_frame, text="Aplicar Cambios y Continuar", command=self.apply_corrections)
        apply_btn.pack(side="left", padx=5)

        proceed_anyway_btn = ttk.Button(btn_frame, text="Continuar Sin Cambios", command=self.proceed_without_corrections)
        proceed_anyway_btn.pack(side="left", padx=5)

        # Initially hide this frame
        self.correction_frame.grid_remove()

    def handle_record_correction(self, patient_records, all_pages, folder_names):
        """Callback from the worker thread to handle record correction in the GUI."""
        self.correction_event = threading.Event()
        self.correction_data = {
            'pages': all_pages,
            'proceed': False
        }

        # Schedule GUI updates in the main thread
        self.root.after(0, self.show_correction_ui, patient_records, all_pages, folder_names)

        # Block the worker thread until the user makes a decision in the GUI
        self.correction_event.wait()
        
        return self.correction_data

    def show_correction_ui(self, patient_records, all_pages, folder_names):
        """Show the correction UI and hide the main UI."""
        # Hide main content
        self.canvas.grid_remove()
        self.scrollbar.grid_remove()
        self.footer_frame.grid_remove()

        # Show correction UI
        self.correction_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Clear previous data
        self.records_tree.delete(*self.records_tree.get_children())
        self.pending_changes = {}
        
        pages_map = {p.page_number: p for p in all_pages}
        records_with_issues = []
        records_without_issues = []
        
        # Separate records with and without issues
        for i, record in enumerate(patient_records):
            folder_name = folder_names[i] if i < len(folder_names) else "SIN CARPETA"
            record_info = (i, record, folder_name)
            
            if record.has_issues:
                records_with_issues.append(record_info)
            else:
                records_without_issues.append(record_info)
        
        # Add records with issues first (highlighted)
        for i, record, folder_name in records_with_issues:
            # Format issues text with proper wrapping
            issues_text = self._format_issues_text(record)
            
            record_node = self.records_tree.insert("", "end", 
                                                text=f"[PROBLEMA] Registro {i+1} ({folder_name})", 
                                                values=("", issues_text),
                                                tags=("error_record",))
            
            self._add_pages_to_record_node(record_node, record, pages_map)
        
        # Add separator if both types exist
        if records_with_issues and records_without_issues:
            self.records_tree.insert("", "end", 
                                    text="── Registros Sin Problemas ──", 
                                    values=("", ""),
                                    tags=("separator",))
        
        # Add records without issues
        for i, record, folder_name in records_without_issues:
            record_node = self.records_tree.insert("", "end", 
                                                text=f"[OK] Registro {i+1} ({folder_name})", 
                                                values=("", "Sin problemas"),
                                                tags=("good_record",))
            
            self._add_pages_to_record_node(record_node, record, pages_map)
        
        # Configure tags for styling - FIXED COLORS
        self.records_tree.tag_configure("error_record", background="#ffebee", foreground="#d32f2f")
        self.records_tree.tag_configure("good_record", background="#e8f5e8", foreground="#388e3c")
        self.records_tree.tag_configure("separator", background="#f5f5f5", foreground="#666666")
        self.records_tree.tag_configure("unknown_page", background="#fff3e0", foreground="#f57c00")  # Orange background, darker text
        self.records_tree.tag_configure("normal_page", background="white", foreground="#333333")  # Dark text on white
        
        # Update summary
        total_records = len(patient_records)
        error_count = len(records_with_issues)
        
        self.summary_label.config(
            text=f"Total: {total_records} registros | Problemas encontrados: {error_count} registros | "
                f"Haga clic en cualquier página para previsualizar, luego use los botones para cambiar la clasificación"
        )
        
        # Expand records with issues automatically
        for child in self.records_tree.get_children():
            item_text = self.records_tree.item(child, "text")
            if "[PROBLEMA]" in item_text:
                self.records_tree.item(child, open=True)

    def _format_issues_text(self, record):
        """Format issues text to prevent overflow."""
        if hasattr(record, 'issues') and record.issues:
            # Join issues and truncate if too long
            issues_text = "; ".join(record.issues)
            if len(issues_text) > 80:  # Adjust based on your column width
                issues_text = issues_text[:77] + "..."
            return issues_text
        else:
            return "Problemas desconocidos"

    def _add_pages_to_record_node(self, record_node, record, pages_map):
        """Helper method to add pages to a record node in the treeview."""
        # Sort all pages in the record
        all_record_pages = []
        
        for attr_name in ['historia_pages', 'cedula_pages', 'recibo_pages', 'unknown_pages']:
            if hasattr(record, attr_name):
                pages = getattr(record, attr_name, [])
                all_record_pages.extend(pages)
        
        # Sort and add pages
        for page_num in sorted(set(all_record_pages)):
            page_info = pages_map.get(page_num)
            if page_info:
                page_type_name = page_info.page_type.name if hasattr(page_info.page_type, 'name') else str(page_info.page_type)
                
                # Determine styling based on page type
                is_unknown = "UNKNOWN" in page_type_name
                
                # Use clear text indicators instead of emojis
                if is_unknown:
                    page_icon = "[REQUIERE REVISIÓN]"
                    tag = "unknown_page"
                else:
                    page_icon = ""
                    tag = "normal_page"
                
                display_text = f"  Página {page_num} {page_icon}".strip()
                
                # Create page node - don't try to set column #0 afterwards
                page_node = self.records_tree.insert(record_node, "end", 
                                    text=display_text, 
                                    values=(page_type_name, ""),
                                    tags=(tag,))
                
                # Store page number as metadata (optional, for easy access)
                # You can store it in a dict if needed: self.page_nodes[page_node] = page_num

    def on_tree_single_click(self, event):
        """Handle single clicks for page selection and editing setup."""
        item_id = self.records_tree.identify_row(event.y)
        if item_id and self.records_tree.parent(item_id):  # Only for page items
            # Show preview
            self.show_page_preview(item_id)
            
            # Set up editing controls
            self._setup_page_editing(item_id)

    def on_tree_double_click(self, event):
        """Handle double-clicks - same as single click for now."""
        self.on_tree_single_click(event)

    def _setup_page_editing(self, item_id):
        """Set up the editing controls for the selected page."""
        # Extract page number from text
        item_text = self.records_tree.item(item_id, "text")
        import re
        match = re.search(r'Página (\d+)', item_text)
        if not match:
            return
        
        page_num = int(match.group(1))
        current_type = self.records_tree.set(item_id, "PageType")
        
        # Store current selection
        self.selected_page_item = item_id
        self.selected_page_num = page_num
        
        # Update the editing controls
        self._update_editing_controls(current_type)

    def _update_editing_controls(self, current_type):
        """Update the editing control buttons."""
        # Update the current type label
        self.current_type_label.config(text=f"Actual: {current_type}")
        
        # Enable all buttons
        for btn in self.type_buttons:
            btn.config(state="normal")
        
        # Highlight current type button
        from src.ocr.text_classifier import PageType
        for page_type, btn in zip([PageType.HISTORIA_CLINICA, PageType.CEDULA, PageType.RECIBO, PageType.UNKNOWN], 
                                self.type_buttons):
            if page_type.name == current_type:
                btn.config(style="Selected.TButton")
            else:
                btn.config(style="TButton")

    def _change_page_type(self, new_type):
        """Change the type of the currently selected page."""
        if not hasattr(self, 'selected_page_item') or not self.selected_page_item:
            return
        
        item_id = self.selected_page_item
        page_num = self.selected_page_num
        
        # Update the display
        self.records_tree.set(item_id, "PageType", new_type.name)
        
        # Store the change
        self.pending_changes[page_num] = new_type
        
        # Update visual feedback
        item_text = self.records_tree.item(item_id, "text")
        if new_type == PageType.UNKNOWN:
            if "[REQUIERE REVISIÓN]" not in item_text:
                updated_text = item_text + " [REQUIERE REVISIÓN]"
                self.records_tree.item(item_id, text=updated_text)
            self.records_tree.item(item_id, tags=("unknown_page",))
        else:
            if "[REQUIERE REVISIÓN]" in item_text:
                updated_text = item_text.replace(" [REQUIERE REVISIÓN]", "")
                self.records_tree.item(item_id, text=updated_text)
            self.records_tree.item(item_id, tags=("normal_page",))
        
        # Update the editing controls
        self._update_editing_controls(new_type.name)
        
        # Show feedback
        self.edit_feedback_label.config(text=f"Cambiado a {new_type.name}", foreground="#27ae60")
        self.root.after(2000, lambda: self.edit_feedback_label.config(text=""))

    def apply_corrections(self):
        """Apply changes from the Treeview and resume processing."""
        # Apply pending changes to the pages data
        if self.pending_changes:
            pages_map = {p.page_number: p for p in self.correction_data['pages']}
            for page_num, new_type in self.pending_changes.items():
                if page_num in pages_map:
                    pages_map[page_num].page_type = new_type
            
            # The 'pages' list in correction_data is updated by reference

        self.correction_data['proceed'] = True
        self.hide_correction_ui()
        self.correction_event.set()

    def proceed_without_corrections(self):
        """Proceed without applying any corrections."""
        self.correction_data['proceed'] = True
        self.hide_correction_ui()
        self.correction_event.set()

    def hide_correction_ui(self):
        """Hide the correction UI and show the main UI."""
        self.correction_frame.grid_remove()
        self.canvas.grid()
        self.scrollbar.grid()
        self.footer_frame.grid()

    def show_page_preview(self, item_id):
        """Show preview for the selected page."""
        item_text = self.records_tree.item(item_id, "text")
        
        # Extract page number
        import re
        match = re.search(r'Página (\d+)', item_text)
        if not match:
            return
        
        page_num = int(match.group(1))
        page_type = self.records_tree.set(item_id, "PageType")
        
        # Update preview label
        self.preview_label.config(text=f"Página {page_num} - {page_type}")
        
        # Clear canvas
        self.preview_canvas.delete("all")
        
        # Get the main PDF path
        main_pdf_path = self.main_path.get()
        if not main_pdf_path or not os.path.exists(main_pdf_path):
            self.preview_canvas.create_text(125, 175, 
                                            text="PDF principal no disponible\npara vista previa", 
                                            justify=tk.CENTER, fill="#666666", font=("Arial", 10))
            return
        
        # Load and display the PDF page in a separate thread to avoid UI blocking
        threading.Thread(
            target=self._load_pdf_preview,
            args=(main_pdf_path, page_num),
            daemon=True
        ).start()

    def _load_pdf_preview(self, pdf_path, page_num):
        """Load PDF page preview in background thread."""
        try:
            # Generate image from PDF page
            pil_image = pdf_page_to_image(pdf_path, page_num, zoom=1.0)  # Lower zoom for preview
            
            # Resize image to fit canvas while maintaining aspect ratio
            canvas_width = 250
            canvas_height = 350
            
            # Calculate scaling
            img_width, img_height = pil_image.size
            scale_w = canvas_width / img_width
            scale_h = canvas_height / img_height
            scale = min(scale_w, scale_h, 1.0)  # Don't upscale
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resize image
            resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage for tkinter
            photo = ImageTk.PhotoImage(resized_image)
            
            # Schedule UI update on main thread
            self.root.after(0, self._update_preview_canvas, photo, new_width, new_height)
            
        except Exception as e:
            error_msg = f"Error al cargar vista previa:\n{str(e)}"
            self.root.after(0, self._show_preview_error, error_msg)

    def _update_preview_canvas(self, photo, img_width, img_height):
        """Update preview canvas with the loaded image (runs on main thread)."""
        # Store reference to prevent garbage collection
        self.preview_photo = photo
        
        # Clear canvas
        self.preview_canvas.delete("all")
        
        # Center the image
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        # Handle case where canvas hasn't been drawn yet
        if canvas_width <= 1:
            canvas_width = 250
        if canvas_height <= 1:
            canvas_height = 350
            
        x = (canvas_width - img_width) // 2
        y = (canvas_height - img_height) // 2
        
        # Create image on canvas
        self.preview_canvas.create_image(x, y, anchor="nw", image=photo)
        
        # Add a border around the image
        self.preview_canvas.create_rectangle(x-1, y-1, x+img_width+1, y+img_height+1, 
                                            outline="#cccccc", width=1)

    def _show_preview_error(self, error_msg):
        """Show error message in preview canvas (runs on main thread)."""
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(125, 175, 
                                        text=error_msg, 
                                        justify=tk.CENTER, fill="#e74c3c", 
                                        font=("Arial", 9), width=200)

    def create_file_input(self, parent, label_text, variable, row):
        """Create a file input row with label, entry, and browse button"""
        ttk.Label(parent, text=label_text).grid(
            row=row*2, column=0, sticky="w", padx=(0, 10), pady=(0, 10))
        
        entry_frame = ttk.Frame(parent)
        entry_frame.grid(row=row*2+1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        entry = ttk.Entry(entry_frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        browse_btn = ttk.Button(entry_frame, text="Examinar", 
                                command=lambda: self.select_file(variable))
        browse_btn.grid(row=0, column=1)
        
        # Path display label
        path_label = ttk.Label(parent, text="", style='Path.TLabel')
        path_label.grid(row=row*2+1, column=0, columnspan=2, sticky="w", pady=(25, 0))
        
        # Update path display when variable changes
        def update_path_display(*args):
            path = variable.get()
            if path:
                filename = os.path.basename(path)
                path_label.config(text=f"Seleccionado: {filename}")
            else:
                path_label.config(text="Ningún archivo seleccionado")
        
        variable.trace('w', update_path_display)
        update_path_display()  # Initial call

    def create_folder_input(self, parent, label_text, variable, row):
        """Create a folder input row with label, entry, and browse button"""
        ttk.Label(parent, text=label_text, style='Section.TLabel').grid(
            row=row*2, column=0, sticky="w", padx=(0, 10), pady=(0, 10))
        
        entry_frame = ttk.Frame(parent)
        entry_frame.grid(row=row*2+1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        entry = ttk.Entry(entry_frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        browse_btn = ttk.Button(entry_frame, text="Examinar", 
                                command=lambda: self.select_folder(variable))
        browse_btn.grid(row=0, column=1)
        
        # Path display label
        path_label = ttk.Label(parent, text="", style='Path.TLabel')
        path_label.grid(row=row*2+1, column=0, columnspan=2, sticky="w", pady=(25, 0))
        
        # Update path display when variable changes
        def update_path_display(*args):
            path = variable.get()
            if path:
                folder_name = os.path.basename(path) or path
                path_label.config(text=f"Salida a: {folder_name}")
            else:
                path_label.config(text="Ninguna carpeta seleccionada")
        
        variable.trace('w', update_path_display)
        update_path_display()  # Initial call

    def select_file(self, variable):
        """Open file dialog for PDF selection"""
        path = filedialog.askopenfilename(
            title="Seleccionar Archivo PDF",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
            initialdir=os.getcwd()
        )
        if path:
            variable.set(path)

    def select_folder(self, variable):
        """Open folder dialog for output directory selection"""
        path = filedialog.askdirectory(
            title="Seleccionar Directorio de Salida",
            initialdir=os.getcwd()
        )
        if path:
            variable.set(path)

    def validate_inputs(self):
        """Validate all input fields before processing"""
        errors = []
        
        if not self.control_path.get().strip():
            errors.append("Se requiere el archivo PDF de control")
        elif not os.path.isfile(self.control_path.get()):
            errors.append("El archivo PDF de control no existe")
        
        if not self.main_path.get().strip():
            errors.append("Se requiere el archivo PDF principal")
        elif not os.path.isfile(self.main_path.get()):
            errors.append("El archivo PDF principal no existe")
        
        if not self.output_dir.get().strip():
            errors.append("Se requiere el directorio de salida")
        elif not os.path.isdir(self.output_dir.get()):
            errors.append("El directorio de salida no existe")
        
        try:
            start_val = int(self.start_value.get())
            if start_val < 0:
                errors.append("El valor de inicio debe ser un número positivo")
        except ValueError:
            errors.append("El valor de inicio debe ser un número válido")
        
        return errors

    def update_progress(self, step, current, total, details=""):
        """Update progress bar and status labels (thread-safe)"""
        # Schedule everything to run on the main loop
        print(f"Callback called from thread: {threading.current_thread().name}")
        print(f"Progress: {step} - {current}/{total} - {details}")
        
        def safe_update():
            self.progress['maximum'] = total
            self.progress['value'] = current

            status_messages = {
                "processing_control_sheet": f"Procesando hoja de control... {details}",
                "splitting_main_pdf": f"Dividiendo PDF principal... {details}",
                "workflow_completed": "¡Procesamiento completado exitosamente!"
            }

            status = status_messages.get(step, f"Procesando: {step}")
            self.status_label.config(text=status)
            
            # Update details
            if details:
                self.details_label.config(text=f"Detalles: {details}")
            else:
                progress_text = f"Progreso: {current}/{total}"
                if total > 0:
                    percentage = (current / total) * 100
                    progress_text += f" ({percentage:.1f}%)"
                self.details_label.config(text=progress_text)

        self.root.after(0, safe_update)

    def set_processing_state(self, processing):
        """Update UI state based on processing status"""
        self.processing = processing

        if processing:
            self.process_btn.config(state="disabled", text="Procesando...")
            self.cancel_btn.config(state="normal")
        else:
            self.process_btn.config(state="normal", text="Iniciar Procesamiento")
            self.cancel_btn.config(state="disabled")

    def run_processing(self):
        """Validate inputs and start processing in background thread"""
        # Validate inputs
        errors = self.validate_inputs()
        if errors:
            error_message = "Por favor corrija los siguientes problemas:\n\n" + "\n".join(f"• {error}" for error in errors)
            messagebox.showerror("Error de Validación", error_message)
            return
        
        try:
            start_val = int(self.start_value.get())
        except ValueError:
            return  # This should be caught by validation

        # Update UI state
        self.set_processing_state(True)
        self.update_progress("starting", 0, 100, "Inicializando...")

        # Start processing in background thread
        self.processing_thread = threading.Thread(
            target=self.process_wrapper,
            args=(
                self.control_path.get(),
                self.main_path.get(),
                self.output_dir.get(),
                start_val
            ),
            daemon=True
        )
        self.processing_thread.start()

    def process_wrapper(self, control, main, output, start_val):
        """Wrapper for the main processing function"""
        try:
            microchip_ids = process_pdfs(
                control, main, output, start_val,
                progress_callback=self.update_progress,
                correction_callback=self.handle_record_correction
            )
            
            def on_success():
                self.set_processing_state(False)
                self.update_progress("completed", 100, 100, "Todos los documentos procesados")
                messagebox.showinfo("Procesamiento Completado", 
                                    f"Se procesaron exitosamente {len(microchip_ids)} carpetas de documentos.\n\n"
                                    f"Salida guardada en: {output}")
            
            self.root.after(0, on_success)

        except Exception as e:
            def on_error(exc):
                self.set_processing_state(False)
                self.status_label.config(text="Procesamiento falló")
                self.details_label.config(text=f"Error: {str(exc)}")
                messagebox.showerror("Error de Procesamiento", 
                                    f"Ocurrió un error durante el procesamiento:\n\n{str(exc)}")
            
            self.root.after(0, on_error, e)

    def cancel_processing(self):
        """Cancel the current processing operation"""
        if self.processing:
            # Note: This is a simple cancel - you might want to implement
            # proper thread cancellation in your processing function
            result = messagebox.askyesno("Cancelar Procesamiento", 
                                        "¿Está seguro de que desea cancelar la operación actual?")
            
            if result:
                self.set_processing_state(False)
                self.status_label.config(text="Procesamiento cancelado por el usuario")
                self.details_label.config(text="")
                self.progress['value'] = 0

    def clear_all_fields(self):
        """Clear all input fields"""
        if self.processing:
            messagebox.showwarning("No se Puede Limpiar", 
                                    "No se pueden limpiar los campos mientras el procesamiento está activo.")
            return
        
        self.control_path.set("")
        self.main_path.set("")
        self.output_dir.set("")
        self.start_value.set("1")
        
        self.status_label.config(text="Listo para procesar documentos")
        self.details_label.config(text="")
        self.progress['value'] = 0