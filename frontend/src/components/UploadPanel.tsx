import { useRef, useState } from 'react';

interface Props {
  onUpload: (file: File) => void;
}

export default function UploadPanel({ onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div
      className={`upload-dropzone ${dragOver ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.md,.txt,.docx"
        onChange={handleChange}
      />
      <p>拖拽或点击上传教材</p>
      <p style={{ fontSize: '11px', color: '#666' }}>支持 PDF / MD / TXT / DOCX</p>
    </div>
  );
}
