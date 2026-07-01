"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadHull, ApiError } from "@/lib/api-client";
import { useHydrostaticsStore } from "@/lib/store";
import { UploadCloud, CheckCircle2, AlertTriangle } from "lucide-react";

export function FileUpload() {
  const [dragActive, setDragActive] = useState(false);
  const { hullUpload, setHullFile, setHullUpload, setUploadError, uploadError } =
    useHydrostaticsStore();

  const mutation = useMutation({
    mutationFn: uploadHull,
    onSuccess: (data) => {
      setHullUpload(data);
      setUploadError(null);
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : "Upload failed.";
      setUploadError(message);
      setHullUpload(null);
    },
  });

  function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".3dm")) {
      setUploadError("Only .3dm files are supported.");
      return;
    }
    setHullFile(file);
    mutation.mutate(file);
  }

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Hull Geometry (.3dm)</label>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        className={`flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed p-6 text-center transition-colors ${
          dragActive ? "border-primary bg-muted" : "border-border"
        }`}
      >
        <UploadCloud className="h-6 w-6 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">
          Drag & drop, or{" "}
          <label className="cursor-pointer text-primary underline">
            browse
            <input
              type="file"
              accept=".3dm"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
              }}
            />
          </label>
        </p>
      </div>

      {mutation.isPending && (
        <p className="text-xs text-muted-foreground">Parsing hull mesh…</p>
      )}

      {hullUpload && !mutation.isPending && (
        <div className="rounded-md bg-muted p-3 text-xs">
          <div className="flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
            {hullUpload.vertex_count.toLocaleString()} vertices ·{" "}
            {hullUpload.face_count.toLocaleString()} faces
          </div>
          <div className="mt-1 text-muted-foreground">
            X: [{hullUpload.bounding_box.x_min.toFixed(2)},{" "}
            {hullUpload.bounding_box.x_max.toFixed(2)}] · Z: [
            {hullUpload.bounding_box.z_min.toFixed(2)},{" "}
            {hullUpload.bounding_box.z_max.toFixed(2)}]
          </div>
          {hullUpload.warnings.map((w, i) => (
            <div key={i} className="mt-1 flex items-start gap-1 text-amber-700">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {uploadError && (
        <div className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-xs text-red-700">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}
    </div>
  );
}
