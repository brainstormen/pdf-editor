import fitz  # PyMuPDF

class PDFDocument:
    def __init__(self):
        self.doc = None
        self.file_path = None

    def open(self, file_path):
        """Open a PDF file."""
        try:
            self.doc = fitz.open(file_path)
            self.file_path = file_path
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False

    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.file_path = None

    def save(self, output_path):
        """Save the document to a new file."""
        if self.doc:
            self.doc.save(output_path)

    def get_page_count(self):
        """Return the number of pages."""
        if self.doc:
            return len(self.doc)
        return 0

    def get_page_image(self, page_number, zoom_factor=2.0):
        """
        Get a rendered image of a specific page.
        Returns a tuple of (bytes, width, height, stride).
        """
        if not self.doc or page_number < 0 or page_number >= len(self.doc):
            return None

        page = self.doc[page_number]
        # zoom_factor allows higher resolution rendering
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        pix = page.get_pixmap(matrix=mat)
        
        # return raw bytes, width, height, and stride (bytes per line)
        return (pix.samples, pix.width, pix.height, pix.stride)

    def add_blank_page(self, position=-1):
        """Insert a blank page."""
        if self.doc:
            self.doc.new_page(position)

    def delete_page(self, page_number):
        """Delete a specific page."""
        if self.doc and 0 <= page_number < len(self.doc):
            self.doc.delete_page(page_number)
