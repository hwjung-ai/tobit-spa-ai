"use client";

import React, { useState } from "react";
import Editor from "@monaco-editor/react";

interface PythonBuilderProps {
  code?: string;
  onChange?: (code: string) => void;
  readOnly?: boolean;
}

// Python library templates
const PYTHON_TEMPLATES = {
  basic: `import pandas as pd
import numpy as np

def main(params: dict, input_payload: dict = None) -> dict:
    """
    Main function for Python API execution
    
    Args:
        params: API parameters (dict)
        input_payload: Additional input payload (optional)
    
    Returns:
        dict: Result with 'columns' and 'rows' keys
    """
    # Your logic here
    result = {
        "columns": [],
        "rows": []
    }
    return result
`,
  data_analysis: `import pandas as pd
import numpy as np
from typing import Dict, Any

def main(params: Dict[str, Any], input_payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Data analysis template
    
    Args:
        params: API parameters including 'table', 'columns'
        input_payload: Additional input payload
    
    Returns:
        dict: Analysis results
    """
    table_name = params.get("table", "")
    columns = params.get("columns", [])
    
    # Load data (placeholder - in production, query from DB)
    # df = pd.read_sql(f"SELECT * FROM {table_name}", connection)
    
    # Data analysis
    results = {
        "columns": ["metric", "value"],
        "rows": [
            {"metric": "mean", "value": 0},
            {"metric": "std", "value": 0},
            {"metric": "count", "value": 0}
        ]
    }
    
    return results
`,
  data_transformation: `import pandas as pd
import numpy as np
from typing import Dict, Any

def main(params: Dict[str, Any], input_payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Data transformation template
    
    Args:
        params: API parameters
        input_payload: Input data to transform
    
    Returns:
        dict: Transformed results
    """
    # Transform input data
    if input_payload and "data" in input_payload:
        df = pd.DataFrame(input_payload["data"])
        
        # Transformations
        df_cleaned = df.dropna()
        df_grouped = df_cleaned.groupby("category").agg({
            "value": ["mean", "std", "count"]
        }).reset_index()
        
        # Flatten multi-index columns
        df_grouped.columns = ["_".join(col).strip() for col in df_grouped.columns.values]
        
        results = {
            "columns": df_grouped.columns.tolist(),
            "rows": df_grouped.to_dict("records")
        }
    else:
        results = {
            "columns": [],
            "rows": []
        }
    
    return results
`,
};

const PYTHON_LIBRARIES = [
  { name: "pandas", import: "import pandas as pd", description: "Data manipulation" },
  { name: "numpy", import: "import numpy as np", description: "Numerical computing" },
  { name: "sqlalchemy", import: "from sqlalchemy import create_engine", description: "Database connection" },
  { name: "requests", import: "import requests", description: "HTTP requests" },
  { name: "json", import: "import json", description: "JSON handling" },
  { name: "datetime", import: "from datetime import datetime", description: "Date/time utilities" },
  { name: "typing", import: "from typing import Dict, Any", description: "Type hints" },
];

const FUNCTION_TEMPLATES = [
  { name: "main", signature: "def main(params: dict, input_payload: dict = None) -> dict:", description: "Main entry point" },
  { name: "load_data", signature: "def load_data(table_name: str) -> pd.DataFrame:", description: "Load data from database" },
  { name: "transform_data", signature: "def transform_data(df: pd.DataFrame) -> pd.DataFrame:", description: "Transform data" },
  { name: "aggregate_data", signature: "def aggregate_data(df: pd.DataFrame, group_by: str) -> pd.DataFrame:", description: "Aggregate data" },
  { name: "export_results", signature: "def export_results(results: dict, format: str = 'json') -> str:", description: "Export results" },
];

export default function PythonBuilder({ code, onChange, readOnly }: PythonBuilderProps) {
  const [pythonCode, setPythonCode] = useState<string>(code || PYTHON_TEMPLATES.basic);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("basic");
  const [selectedLibrary, setSelectedLibrary] = useState<string>("");
  const [selectedFunction, setSelectedFunction] = useState<string>("");

  const handleTemplateChange = (templateName: string) => {
    setSelectedTemplate(templateName);
    setPythonCode(PYTHON_TEMPLATES[templateName as keyof typeof PYTHON_TEMPLATES]);
  };

  const handleLibraryInsert = (library: { name: string; import: string }) => {
    const importLine = library.import;
    if (!pythonCode.includes(importLine)) {
      const updatedCode = importLine + "\n\n" + pythonCode;
      setPythonCode(updatedCode);
    }
  };

  const handleFunctionInsert = (func: { name: string; signature: string; description: string }) => {
    const functionBody = `\n\n${func.signature}\n    """${func.description}"""\n    # TODO: Implement\n    pass\n`;
    const updatedCode = pythonCode + functionBody;
    setPythonCode(updatedCode);
  };

  const handleCodeChange = (value: string | undefined) => {
    const newCode = value || "";
    setPythonCode(newCode);
    if (onChange) {
      onChange(newCode);
    }
  };

  const testPythonCode = async () => {
    // In production, this would execute the Python code in a sandbox
    console.log("Testing Python code...");
    console.log(pythonCode);
    alert("Python code test would execute here. (In production, integrate with Pyodide or backend Python executor)");
  };

  return (
    <div className="space-y-4 rounded-2xl p-4" style={{border: "1px solid var(--border)", backgroundColor: "rgba(15, 23, 42, 0.4)"}}>
      <h3 className="text-xs uppercase tracking-normal " style={{color: "var(--muted-foreground)"}}>Python Builder</h3>

      {/* Template Selection */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Templates</label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.keys(PYTHON_TEMPLATES).map((template) => (
            <button
              key={template}
              onClick={() => handleTemplateChange(template)}
              disabled={readOnly}
              className={`rounded-2xl border px-3 py-2 text-[11px] font-semibold uppercase tracking-normal transition ${
                selectedTemplate === template
                  ? "border-sky-500 bg-sky-500/10 text-white"
                  : "hover:"
              }`}
              style={
                selectedTemplate === template
                  ? { borderColor: "var(--border)" }
                  : { border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)", color: "var(--muted-foreground)" }
              }
            >
              {template}
            </button>
          ))}
        </div>
      </div>

      {/* Library Suggestions */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Add Library Import</label>
        <div className="flex gap-2">
          <select
            value={selectedLibrary}
            onChange={(e) => setSelectedLibrary(e.target.value)}
            disabled={readOnly}
            className="flex-1 rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-sky-500" style={{border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
          >
            <option value="">-- Select library --</option>
            {PYTHON_LIBRARIES.map((lib) => (
              <option key={lib.name} value={lib.name}>
                {lib.name} - {lib.description}
              </option>
            ))}
          </select>
          <button
            onClick={() => selectedLibrary && handleLibraryInsert(PYTHON_LIBRARIES.find(l => l.name === selectedLibrary)!)}
            disabled={!selectedLibrary || readOnly}
            className="rounded-2xl border border-sky-500/30 bg-sky-500/80 px-4 py-2 text-[11px] font-bold uppercase tracking-normal text-white transition hover:bg-sky-400 disabled: disabled:" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}
          >
            Insert
          </button>
        </div>
      </div>

      {/* Function Templates */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Add Function Template</label>
        <div className="flex gap-2">
          <select
            value={selectedFunction}
            onChange={(e) => setSelectedFunction(e.target.value)}
            disabled={readOnly}
            className="flex-1 rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-sky-500" style={{border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)", color: "var(--foreground)"}}
          >
            <option value="">-- Select function --</option>
            {FUNCTION_TEMPLATES.map((func) => (
              <option key={func.name} value={func.name}>
                {func.name} - {func.description}
              </option>
            ))}
          </select>
          <button
            onClick={() => selectedFunction && handleFunctionInsert(FUNCTION_TEMPLATES.find(f => f.name === selectedFunction)!)}
            disabled={!selectedFunction || readOnly}
            className="rounded-2xl border border-indigo-500/30 bg-indigo-500/80 px-4 py-2 text-[11px] font-bold uppercase tracking-normal text-white transition hover:bg-indigo-400 disabled: disabled:" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}
          >
            Insert
          </button>
        </div>
      </div>

      {/* Code Editor */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Python Code</label>
        <div className="rounded-2xl border" style={{border: "1px solid var(--border)", backgroundColor: "var(--surface-overlay)"}}>
          <Editor
            height="400px"
            language="python"
            value={pythonCode}
            onChange={handleCodeChange}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              readOnly,
              automaticLayout: true,
              scrollBeyondLastLine: false,
              wordWrap: "on",
              lineNumbers: "on",
              renderWhitespace: "selection",
              folding: true,
              bracketPairColorization: { enabled: true },
            }}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-normal " style={{color: "var(--muted-foreground)"}}>
          Python 3.11+ syntax
        </div>
        <button
          onClick={testPythonCode}
          disabled={readOnly}
          className="rounded-full border border-emerald-500/30 bg-emerald-500/80 px-6 py-2 text-[11px] font-bold uppercase tracking-wider text-white transition hover:bg-emerald-400 hover:shadow-[0_0_15px_rgba(16,185,129,0.3)] disabled: disabled:" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}
        >
          Test Code
        </button>
      </div>

      {/* Help Section */}
      <div className="space-y-2 rounded-2xl border p-3" style={{border: "1px solid var(--border)", backgroundColor: "rgba(15, 23, 42, 0.4)"}}>
        <h4 className="text-xs uppercase tracking-normal" style={{color: "var(--muted-foreground)"}}>Quick Help</h4>
        <div className="space-y-1 text-[11px]" style={{color: "var(--muted-foreground)"}}>
          <p>• <span className="font-mono text-sky-400">main()</span> function is required for execution</p>
          <p>• Return <span className="font-mono text-sky-400">{"{columns: [...], rows: [...]}"}</span> for table results</p>
          <p>• Use <span className="font-mono text-sky-400">params</span> dict for API parameters</p>
          <p>• Use <span className="font-mono text-sky-400">input_payload</span> for additional input data</p>
          <p>• Available libraries: pandas, numpy, sqlalchemy, requests</p>
        </div>
      </div>
    </div>
  );
}
