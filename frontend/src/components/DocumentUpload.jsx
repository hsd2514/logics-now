import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

export function DocumentUpload({ onUpload }) {
  const [selectedType, setSelectedType] = useState('LR')
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState([])

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prev => [...prev, ...acceptedFiles.map(file => ({
      file,
      status: 'pending',
      id: Math.random().toString(36).substr(2, 9)
    }))])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
      'application/pdf': ['.pdf'],
      'text/html': ['.html', '.htm']
    }
  })

  const handleUpload = async () => {
    if (files.length === 0) return
    
    setUploading(true)
    const uploadResults = []

    for (const fileItem of files) {
      try {
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'uploading' } : f
        ))
        
        const result = await onUpload(fileItem.file, selectedType)
        
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'success', result } : f
        ))
        uploadResults.push({ ...fileItem, status: 'success', result })
      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, status: 'error', error: error.message } : f
        ))
        uploadResults.push({ ...fileItem, status: 'error', error: error.message })
      }
    }

    setResults(uploadResults)
    setUploading(false)
  }

  const clearFiles = () => {
    setFiles([])
    setResults([])
  }

  const docTypes = [
    { value: 'LR', label: 'Lorry Receipt', color: 'bg-blue-500' },
    { value: 'POD', label: 'Proof of Delivery', color: 'bg-green-500' },
    { value: 'INVOICE', label: 'Invoice', color: 'bg-purple-500' },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Documents
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Document Type Selection */}
        <div className="flex gap-2">
          {docTypes.map(type => (
            <Button
              key={type.value}
              variant={selectedType === type.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedType(type.value)}
            >
              {type.label}
            </Button>
          ))}
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
          `}
        >
          <input {...getInputProps()} />
          <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
          {isDragActive ? (
            <p>Drop the files here...</p>
          ) : (
            <div>
              <p className="font-medium">Drag & drop files here</p>
              <p className="text-sm text-muted-foreground mt-1">
                or click to select files (PNG, JPG, PDF, HTML)
              </p>
            </div>
          )}
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">{files.length} file(s) selected</span>
              <Button variant="ghost" size="sm" onClick={clearFiles}>Clear all</Button>
            </div>
            <div className="max-h-40 overflow-y-auto space-y-2">
              {files.map(item => (
                <div key={item.id} className="flex items-center gap-2 p-2 bg-muted rounded">
                  <FileText className="h-4 w-4" />
                  <span className="flex-1 text-sm truncate">{item.file.name}</span>
                  {item.status === 'pending' && (
                    <Badge variant="secondary">Pending</Badge>
                  )}
                  {item.status === 'uploading' && (
                    <Badge variant="outline">Uploading...</Badge>
                  )}
                  {item.status === 'success' && (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  )}
                  {item.status === 'error' && (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload Button */}
        <Button
          className="w-full"
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
        >
          {uploading ? 'Uploading...' : `Upload as ${selectedType}`}
        </Button>
      </CardContent>
    </Card>
  )
}
