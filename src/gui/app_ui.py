import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os

from src.pdf.main_processor import process_pdfs

class PDFApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.build_ui()

    def setup_window(self):
        """Configure main window properties"""
        self.root.title("PDF Processor - Document Processing Tool")
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
        self.create_footer()

    def create_header(self):
        """Create application header"""
        header_frame = ttk.Frame(self.root)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_label = ttk.Label(header_frame, text="PDF Document Processor", 
                                style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                    text="Process and split PDF documents based on control sheets",
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
        files_frame = ttk.LabelFrame(parent, text="Input Files", padding=15)
        files_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        files_frame.grid_columnconfigure(1, weight=1)
        
        self.create_file_input(files_frame, "Control PDF:", self.control_path, 0)
        self.create_file_input(files_frame, "Main PDF:", self.main_path, 1)
        
        # Output section
        output_frame = ttk.LabelFrame(parent, text="Output", padding=15)
        output_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        output_frame.grid_columnconfigure(1, weight=1)
        
        self.create_folder_input(output_frame, "Output Directory:", self.output_dir, 0)

    def create_config_section(self, parent):
        """Create configuration section"""
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding=15)
        config_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        config_frame.grid_columnconfigure(1, weight=1)
        
        # Start value input
        ttk.Label(config_frame, text="Start Value:", style='Section.TLabel').grid(
            row=0, column=0, sticky="w", padx=(0, 10))
        
        start_entry = ttk.Entry(config_frame, textvariable=self.start_value, width=15)
        start_entry.grid(row=0, column=1, sticky="w")
        
        # Add tooltip-like help text
        help_text = ttk.Label(config_frame, 
                                text="Starting number for document processing sequence",
                                font=('Arial', 8),
                                foreground='#95a5a6')
        help_text.grid(row=1, column=1, sticky="w", pady=(2, 0))

    def create_progress_section(self, parent):
        """Create progress tracking section"""
        progress_frame = ttk.LabelFrame(parent, text="Processing Status", padding=15)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(progress_frame, text="Ready to process documents")
        self.status_label.grid(row=1, column=0, sticky="w")
        
        # Progress details label
        self.details_label = ttk.Label(progress_frame, text="", font=('Arial', 8))
        self.details_label.grid(row=2, column=0, sticky="w", pady=(2, 0))

    def create_footer(self):
        """Create footer with action buttons"""
        footer_frame = ttk.Frame(self.root)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))

        # Button frame
        button_frame = ttk.Frame(footer_frame)
        button_frame.pack(anchor="center")
        
        # Process button
        self.process_btn = ttk.Button(button_frame, text="Start Processing", 
                                        command=self.run_processing,
                                        style='Processing.TButton')
        self.process_btn.pack(side="left", padx=(0, 10))
        
        # Cancel button (initially disabled)
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", 
                                    command=self.cancel_processing,
                                    state="disabled")
        self.cancel_btn.pack(side="left", padx=(10, 0))
        
        # Clear button
        clear_btn = ttk.Button(button_frame, text="Clear All", 
                                command=self.clear_all_fields)
        clear_btn.pack(side="left", padx=(10, 0))

    def create_file_input(self, parent, label_text, variable, row):
        """Create a file input row with label, entry, and browse button"""
        ttk.Label(parent, text=label_text, style='Section.TLabel').grid(
            row=row*2, column=0, sticky="w", padx=(0, 10), pady=(0, 10))
        
        entry_frame = ttk.Frame(parent)
        entry_frame.grid(row=row*2+1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        entry = ttk.Entry(entry_frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        browse_btn = ttk.Button(entry_frame, text="Browse", 
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
                path_label.config(text=f"Selected: {filename}")
            else:
                path_label.config(text="No file selected")
        
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
        
        browse_btn = ttk.Button(entry_frame, text="Browse", 
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
                path_label.config(text=f"Output to: {folder_name}")
            else:
                path_label.config(text="No folder selected")
        
        variable.trace('w', update_path_display)
        update_path_display()  # Initial call

    def select_file(self, variable):
        """Open file dialog for PDF selection"""
        path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        if path:
            variable.set(path)

    def select_folder(self, variable):
        """Open folder dialog for output directory selection"""
        path = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=os.getcwd()
        )
        if path:
            variable.set(path)

    def validate_inputs(self):
        """Validate all input fields before processing"""
        errors = []
        
        if not self.control_path.get().strip():
            errors.append("Control PDF file is required")
        elif not os.path.isfile(self.control_path.get()):
            errors.append("Control PDF file does not exist")
        
        if not self.main_path.get().strip():
            errors.append("Main PDF file is required")
        elif not os.path.isfile(self.main_path.get()):
            errors.append("Main PDF file does not exist")
        
        if not self.output_dir.get().strip():
            errors.append("Output directory is required")
        elif not os.path.isdir(self.output_dir.get()):
            errors.append("Output directory does not exist")
        
        try:
            start_val = int(self.start_value.get())
            if start_val < 0:
                errors.append("Start value must be a positive number")
        except ValueError:
            errors.append("Start value must be a valid number")
        
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
                "processing_control_sheet": f"Processing control sheet... {details}",
                "splitting_main_pdf": f"Splitting main PDF... {details}",
                "workflow_completed": "Processing completed successfully!"
            }

            status = status_messages.get(step, f"Processing: {step}")
            self.status_label.config(text=status)
            
            # Update details
            if details:
                self.details_label.config(text=f"Details: {details}")
            else:
                progress_text = f"Progress: {current}/{total}"
                if total > 0:
                    percentage = (current / total) * 100
                    progress_text += f" ({percentage:.1f}%)"
                self.details_label.config(text=progress_text)

        self.root.after(0, safe_update)

    def set_processing_state(self, processing):
        """Update UI state based on processing status"""
        self.processing = processing

        if processing:
            self.process_btn.config(state="disabled", text="Processing...")
            self.cancel_btn.config(state="normal")
        else:
            self.process_btn.config(state="normal", text="Start Processing")
            self.cancel_btn.config(state="disabled")

    def run_processing(self):
        """Validate inputs and start processing in background thread"""
        # Validate inputs
        errors = self.validate_inputs()
        if errors:
            error_message = "Please fix the following issues:\n\n" + "\n".join(f"• {error}" for error in errors)
            messagebox.showerror("Validation Error", error_message)
            return
        
        try:
            start_val = int(self.start_value.get())
        except ValueError:
            return  # This should be caught by validation

        # Update UI state
        self.set_processing_state(True)
        self.update_progress("starting", 0, 100, "Initializing...")

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
                progress_callback=self.update_progress
            )
            
            def on_success():
                self.set_processing_state(False)
                self.update_progress("completed", 100, 100, "All documents processed")
                messagebox.showinfo("Processing Complete", 
                                    f"Successfully processed {len(microchip_ids)} document folders.\n\n"
                                    f"Output saved to: {output}")
            
            self.root.after(0, on_success)

        except Exception as e:
            def on_error():
                self.set_processing_state(False)
                self.status_label.config(text="Processing failed")
                self.details_label.config(text=f"Error: {str(e)}")
                messagebox.showerror("Processing Error", 
                                    f"An error occurred during processing:\n\n{str(e)}")
            
            self.root.after(0, on_error)

    def cancel_processing(self):
        """Cancel the current processing operation"""
        if self.processing:
            # Note: This is a simple cancel - you might want to implement
            # proper thread cancellation in your processing function
            result = messagebox.askyesno("Cancel Processing", 
                                        "Are you sure you want to cancel the current operation?")
            
            if result:
                self.set_processing_state(False)
                self.status_label.config(text="Processing cancelled by user")
                self.details_label.config(text="")
                self.progress['value'] = 0

    def clear_all_fields(self):
        """Clear all input fields"""
        if self.processing:
            messagebox.showwarning("Cannot Clear", 
                                    "Cannot clear fields while processing is active.")
            return
        
        self.control_path.set("")
        self.main_path.set("")
        self.output_dir.set("")
        self.start_value.set("1")
        
        self.status_label.config(text="Ready to process documents")
        self.details_label.config(text="")
        self.progress['value'] = 0