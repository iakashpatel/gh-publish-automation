import React, { useState } from 'react';

function App() {
  const [jsonData, setJsonData] = useState({});
  const [file, setFile] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");

  // Handle file upload
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsedJson = JSON.parse(reader.result);
        setJsonData(parsedJson);
        setFile(file);
      } catch (error) {
        console.error("Invalid JSON file", error);
      }
    };
    reader.readAsText(file);
  };

  // Handle JSON editing in the form
  const handleJsonChange = (e) => {
    try {
      const updatedJson = JSON.parse(e.target.value);
      setJsonData(updatedJson);
    } catch (error) {
      console.error("Invalid JSON format", error);
    }
  };

  // Submit edited JSON to the backend API
  const handleSubmit = async () => {
    const requestData = {
      user_id: "user123",  // Placeholder user ID, can be replaced with actual user ID or email
      pr_comment: "Editing JSON data",
      file_path: `files/${file.name}`,
      file_content: jsonData,
      branch_name: "json-update"
    };

    try {
      const response = await fetch("http://localhost:5000/submit-changes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData)
      });
      const result = await response.json();

      if (response.ok) {
        setStatusMessage(`Pull request created successfully: ${result.pr_url}`);
      } else {
        setStatusMessage(`Error: ${result.error}`);
      }
    } catch (error) {
      setStatusMessage(`Request failed: ${error.message}`);
    }
  };

  return (
    <div>
      <h1>JSON Editor</h1>
      <input type="file" onChange={handleFileUpload} />
      <textarea
        rows="20"
        cols="80"
        value={JSON.stringify(jsonData, null, 2)}
        onChange={handleJsonChange}
      ></textarea>
      <button onClick={handleSubmit}>Submit Changes</button>
      <p>{statusMessage}</p>
    </div>
  );
}

export default App;
