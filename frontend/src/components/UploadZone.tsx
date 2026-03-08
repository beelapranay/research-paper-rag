import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onUpload: (files: File[]) => void;
}

const UploadZone = ({ onUpload }: UploadZoneProps) => {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      onUpload(acceptedFiles);
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all duration-200",
        "hover:border-primary hover:bg-primary/5",
        isDragActive
          ? "border-primary bg-primary/10 scale-[1.02]"
          : "border-border"
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2 py-2">
        {isDragActive ? (
          <FileText className="h-8 w-8 text-primary animate-pulse-soft" />
        ) : (
          <Upload className="h-8 w-8 text-muted-foreground" />
        )}
        <p className="text-sm font-medium text-foreground">
          {isDragActive ? "Drop PDFs here" : "Drop PDFs or browse"}
        </p>
        <p className="text-xs text-muted-foreground">Accepts multiple files</p>
      </div>
    </div>
  );
};

export default UploadZone;
