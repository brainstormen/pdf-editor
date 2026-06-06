document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadView = document.getElementById('upload-view');
    const editorView = document.getElementById('editor-view');
    const closeBtn = document.getElementById('close-pdf');
    const canvasContainer = document.getElementById('pdf-canvas-container');
    const thumbnailsContainer = document.getElementById('thumbnails-container');

    // Drag and Drop Events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        if (file.type !== 'application/pdf') {
            alert('Please upload a valid PDF file.');
            return;
        }

        // Switch UI to editor
        uploadView.classList.remove('active');
        uploadView.classList.add('hidden');
        editorView.classList.remove('hidden');
        editorView.classList.add('active');

        // Prepare formData
        const formData = new FormData();
        formData.append('file', file);

        // Upload to backend
        uploadPDF(formData);
    }

    let currentFileId = null;
    let currentPage = 0;
    let currentTool = 'select'; // 'select', 'text', 'erase'
    let annotations = []; // Array to store user actions
    
    // Tool selection
    const toolBtns = document.querySelectorAll('.tool-btn[data-tool]');
    toolBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            toolBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTool = btn.dataset.tool;
            
            const layer = document.getElementById('interactive-layer');
            if(layer) {
                layer.className = `interactive-layer tool-${currentTool}`;
            }
        });
    });

    // Save Button
    document.getElementById('save-pdf').addEventListener('click', async () => {
        if(!currentFileId) return;
        
        try {
            const btn = document.getElementById('save-pdf');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
            btn.disabled = true;

            const response = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: currentFileId,
                    page_num: currentPage,
                    actions: annotations
                })
            });

            if (!response.ok) throw new Error('Save failed');

            // Download the returned file
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `edited_document.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            btn.innerHTML = originalText;
            btn.disabled = false;
        } catch(err) {
            console.error(err);
            alert('Failed to save document');
            document.getElementById('save-pdf').disabled = false;
            document.getElementById('save-pdf').innerHTML = '<i class="fa-solid fa-download"></i> Save';
        }
    });

    async function uploadPDF(formData) {
        try {
            canvasContainer.innerHTML = '<div class="spinner"></div><p>Processing document...</p>';
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');

            const data = await response.json();
            currentFileId = data.file_id;
            currentPage = 0;
            annotations = []; // Reset annotations

            // Fetch the first page as image
            loadPage(currentFileId, currentPage);

        } catch (error) {
            console.error('Error:', error);
            alert('Failed to upload document.');
            closeEditor();
        }
    }

    async function loadPage(fileId, pageNum) {
        try {
            canvasContainer.innerHTML = '<div class="spinner"></div>';
            
            const response = await fetch(`/api/page/${fileId}/${pageNum}`);
            if (!response.ok) throw new Error('Failed to load page');

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            // Create wrapper
            canvasContainer.innerHTML = `
                <div class="pdf-wrapper" id="pdf-wrapper">
                    <img src="${url}" class="pdf-page-img" id="pdf-page-img" alt="PDF Page ${pageNum + 1}">
                    <div class="interactive-layer tool-${currentTool}" id="interactive-layer"></div>
                </div>
            `;
            
            thumbnailsContainer.innerHTML = `<div class="thumbnail"><img src="${url}" style="width:100%; border-radius:4px;"></div>`;
            
            setupInteractiveLayer();

        } catch (error) {
            console.error('Error:', error);
            canvasContainer.innerHTML = '<div class="canvas-placeholder"><i class="fa-solid fa-circle-exclamation"></i><p>Failed to load page</p></div>';
        }
    }

    function setupInteractiveLayer() {
        const layer = document.getElementById('interactive-layer');
        let isDrawing = false;
        let startX, startY;
        let selectionBox = null;

        layer.addEventListener('mousedown', (e) => {
            if (e.target !== layer) return; // Ignore if clicking on an annotation

            const rect = layer.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;

            if (currentTool === 'text') {
                addTextInput(startX, startY);
            } else if (currentTool === 'erase') {
                isDrawing = true;
                selectionBox = document.createElement('div');
                selectionBox.className = 'selection-box';
                selectionBox.style.left = startX + 'px';
                selectionBox.style.top = startY + 'px';
                layer.appendChild(selectionBox);
            }
        });

        layer.addEventListener('mousemove', (e) => {
            if (!isDrawing || !selectionBox) return;
            const rect = layer.getBoundingClientRect();
            const currentX = e.clientX - rect.left;
            const currentY = e.clientY - rect.top;

            const width = Math.abs(currentX - startX);
            const height = Math.abs(currentY - startY);
            const left = Math.min(currentX, startX);
            const top = Math.min(currentY, startY);

            selectionBox.style.width = width + 'px';
            selectionBox.style.height = height + 'px';
            selectionBox.style.left = left + 'px';
            selectionBox.style.top = top + 'px';
        });

        layer.addEventListener('mouseup', (e) => {
            if (isDrawing && selectionBox) {
                isDrawing = false;
                
                const w = parseInt(selectionBox.style.width || '0');
                const h = parseInt(selectionBox.style.height || '0');
                
                if (w > 5 && h > 5) {
                    // Create a permanent redact element
                    const redact = document.createElement('div');
                    redact.className = 'redact-annot';
                    redact.style.left = selectionBox.style.left;
                    redact.style.top = selectionBox.style.top;
                    redact.style.width = selectionBox.style.width;
                    redact.style.height = selectionBox.style.height;
                    
                    // Add delete button logic later if needed
                    layer.appendChild(redact);
                    
                    // Save to annotations array
                    annotations.push({
                        type: 'redact',
                        x: parseInt(selectionBox.style.left),
                        y: parseInt(selectionBox.style.top),
                        w: w,
                        h: h,
                        // We also need the original image scale to translate coordinates
                        imgWidth: layer.offsetWidth,
                        imgHeight: layer.offsetHeight
                    });
                }
                
                layer.removeChild(selectionBox);
                selectionBox = null;
            }
        });

        function addTextInput(x, y) {
            const input = document.createElement('textarea');
            input.className = 'text-annot';
            input.style.left = x + 'px';
            input.style.top = y + 'px';
            input.placeholder = "Type text here...";
            layer.appendChild(input);
            input.focus();

            // When unfocused, save it if not empty
            input.addEventListener('blur', () => {
                if (input.value.trim() === '') {
                    layer.removeChild(input);
                } else {
                    // Make it look like plain text
                    input.style.border = 'none';
                    input.style.background = 'transparent';
                    input.readOnly = true;
                    
                    annotations.push({
                        type: 'text',
                        text: input.value,
                        x: x,
                        y: y,
                        w: input.offsetWidth,
                        h: input.offsetHeight,
                        fontSize: 16,
                        imgWidth: layer.offsetWidth,
                        imgHeight: layer.offsetHeight
                    });
                }
            });
        }
    }

    function closeEditor() {
        editorView.classList.remove('active');
        editorView.classList.add('hidden');
        uploadView.classList.remove('hidden');
        uploadView.classList.add('active');
        fileInput.value = '';
        currentFileId = null;
        annotations = [];
    }

    closeBtn.addEventListener('click', closeEditor);
});
