import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/Toaster';
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export function BatchUploadProgress({ onClose, onComplete }) {
  const [files, setFiles] = useState([]);
  const [docType, setDocType] = useState('LR');
  const [uploading, setUploading] = useState(false);
  const [batchProgress, setBatchProgress] = useState(null);
  const [fileStatuses, setFileStatuses] = useState({});
  const [ws, setWs] = useState(null);
  const { addToast } = useToast();

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected for batch upload');
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'batch_start':
          setBatchProgress({
            batchId: data.batch_id,
            total: data.total_files,
            current: 0,
            docType: data.doc_type
          });
          break;
          
        case 'batch_progress':
          setBatchProgress(prev => ({
            ...prev,
            current: data.current,
            fileName: data.file_name,
            progress: data.progress
          }));
          break;
          
        case 'processing_update':
          // Update individual file progress
          setFileStatuses(prev => ({
            ...prev,
            [data.document_id]: {
              stage: data.stage,
              progress: data.progress,
              message: data.message
            }
          }));
          break;
          
        case 'batch_file_complete':
          setFileStatuses(prev => ({
            ...prev,
            [data.document_id]: {
              stage: 'DONE',
              progress: 100,
              message: 'Complete',
              fileName: data.file_name,
              status: data.status
            }
          }));
          break;
          
        case 'batch_file_error':
          setFileStatuses(prev => ({
            ...prev,
            [data.file_name]: {
              stage: 'ERROR',
              progress: 0,
              message: data.error,
              fileName: data.file_name,
              status: 'ERROR'
            }
          }));
          break;
          
        case 'batch_complete':
          setBatchProgress(prev => ({
            ...prev,
            complete: true,
            successful: data.successful,
            failed: data.failed
          }));
          setUploading(false);
          addToast(`Batch upload complete: ${data.successful}/${data.total} successful`, 'success');
          if (onComplete) onComplete();
          break;
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setFiles(selectedFiles);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      addToast('Please select files to upload', 'warning');
      return;
    }

    setUploading(true);
    setFileStatuses({});
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await fetch(`/api/documents/batch?doc_type=${docType}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const results = await response.json();
      console.log('Upload results:', results);
    } catch (error) {
      addToast(`Upload error: ${error.message}`, 'error');
      setUploading(false);
    }
  };

  const getStageLabel = (stage) => {
    const stages = {
      'PREPROCESSING': 'Pre-processing',
      'OCR': 'OCR Extraction',
      'NER': 'Entity Extraction',
      'EXTRACTION': 'Text Extraction',
      'DONE': 'Complete',
      'ERROR': 'Error'
    };
    return stages[stage] || stage;
  };

  const getStageIcon = (stage, progress) => {
    if (stage === 'DONE') return <CheckCircle className="w-5 h-5 text-green-500" />;
    if (stage === 'ERROR') return <AlertCircle className="w-5 h-5 text-red-500" />;
    return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
  };

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Batch Document Upload</CardTitle>
          {onClose && (
            <Button onClick={onClose} variant="ghost" size="sm">
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* File Selection */}
        {!uploading && !batchProgress?.complete && (
          <div className="space-y-4">
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium mb-2">
                  Select Files
                </label>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg,.html,.htm"
                  onChange={handleFileSelect}
                  className="w-full p-2 border rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Document Type
                </label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="px-4 py-2 border rounded-md"
                >
                  <option value="LR">LR (Loading Receipt)</option>
                  <option value="POD">POD (Proof of Delivery)</option>
                  <option value="INVOICE">Invoice</option>
                </select>
              </div>
            </div>

            {files.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">
                  {files.length} file(s) selected
                </p>
                <div className="max-h-32 overflow-y-auto border rounded-md p-2 space-y-1">
                  {files.map((file, idx) => (
                    <div key={idx} className="text-sm flex items-center gap-2">
                      <span className="text-muted-foreground">{idx + 1}.</span>
                      <span className="truncate">{file.name}</span>
                      <span className="text-xs text-muted-foreground">
                        ({(file.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading}
              className="w-full"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload {files.length} Document{files.length !== 1 ? 's' : ''}
            </Button>
          </div>
        )}

        {/* Overall Progress */}
        {batchProgress && (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">
                  Overall Progress: {batchProgress.current || 0} / {batchProgress.total}
                </span>
                <span className="text-sm text-muted-foreground">
                  {Math.round(batchProgress.progress || 0)}%
                </span>
              </div>
              <Progress value={batchProgress.progress || 0} className="h-2" />
            </div>

            {batchProgress.fileName && !batchProgress.complete && (
              <div className="text-sm text-muted-foreground">
                Processing: <span className="font-medium">{batchProgress.fileName}</span>
              </div>
            )}

            {batchProgress.complete && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-6 h-6 text-green-500" />
                  <div>
                    <p className="font-semibold">Batch Upload Complete!</p>
                    <p className="text-sm text-muted-foreground">
                      {batchProgress.successful} successful, {batchProgress.failed} failed
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Individual File Progress */}
        {Object.keys(fileStatuses).length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">File Processing Details</h4>
            <div className="max-h-64 overflow-y-auto space-y-2 border rounded-md p-3">
              {Object.entries(fileStatuses).map(([id, status]) => (
                <div key={id} className="border rounded-lg p-3 bg-muted/30">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStageIcon(status.stage, status.progress)}
                      <span className="text-sm font-medium truncate max-w-xs">
                        {status.fileName || id}
                      </span>
                    </div>
                    <Badge
                      variant={status.stage === 'DONE' ? 'default' : status.stage === 'ERROR' ? 'destructive' : 'secondary'}
                    >
                      {getStageLabel(status.stage)}
                    </Badge>
                  </div>
                  {status.stage !== 'DONE' && status.stage !== 'ERROR' && (
                    <>
                      <Progress value={status.progress} className="h-1 mb-1" />
                      <p className="text-xs text-muted-foreground">{status.message}</p>
                    </>
                  )}
                  {status.stage === 'ERROR' && (
                    <p className="text-xs text-red-500">{status.message}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {batchProgress?.complete && (
          <div className="flex gap-2">
            <Button onClick={() => {
              setFiles([]);
              setBatchProgress(null);
              setFileStatuses({});
            }} className="flex-1">
              Upload More
            </Button>
            {onClose && (
              <Button onClick={onClose} variant="outline" className="flex-1">
                Close
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
