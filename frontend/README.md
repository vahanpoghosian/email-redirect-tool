# React Frontend for Domain Redirect Tool

This is the modern React frontend that provides a reliable, interactive interface for managing domain redirections.

## 🚀 Features

- ✅ **Working Save Buttons** - Reliable form submissions with real-time feedback
- ✅ **Real-time Progress Bar** - Live updates every second during domain sync
- ✅ **Client Auto-fill** - Dropdown selection automatically fills redirect URLs
- ✅ **Bulk Updates** - Select multiple domains and update all at once
- ✅ **Status Tracking** - Clear visual feedback for all operations

## 📋 Setup Instructions

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm start
```

The React app will open at: **http://localhost:3000**

### 3. Backend Connection
The React app connects to your Flask backend at `http://localhost:5000` via proxy configuration.

Make sure your Flask backend is running:
```bash
# In the main project directory
python app.py
```

## 🔧 How It Works

### Save Button
- Click "Save" next to any redirect URL
- Shows "Updating..." status immediately
- Updates Namecheap via API
- Verifies the change was successful
- Shows ✅ "Synced & Verified" or ❌ "Failed" status

### Progress Bar
- Polls backend every 1 second during sync operations
- Shows percentage complete and current domain
- Displays live counts of added/updated/errors
- Auto-refreshes page when sync completes

### Client Auto-fill
- Select a client from dropdown
- Automatically fills redirect URL field with client's URL
- Save button works normally after auto-fill

### Bulk Updates
- Select multiple domains with checkboxes
- Click "Bulk Update" button
- Choose manual URL or client URL
- Updates all selected domains at once

## 🏗️ Build for Production

```bash
npm run build
```

This creates a `build/` directory with optimized files that can be served by the Flask backend.

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── DomainTable.js      # Main table with save buttons
│   │   ├── SyncProgress.js     # Real-time progress bar
│   │   ├── BulkUpdateModal.js  # Bulk update functionality
│   │   └── ClientManager.js    # Client management
│   ├── App.js                  # Main app component
│   ├── index.js               # React entry point
│   └── index.css              # Styles
├── public/
│   └── index.html             # HTML template
└── package.json               # Dependencies and scripts
```

## 🔗 API Endpoints Used

- `GET /api/domains` - Load all domains
- `GET /api/clients` - Load all clients
- `POST /update-redirect` - Save individual redirect
- `POST /api/bulk-update` - Bulk update domains
- `POST /sync-domains` - Start domain sync
- `GET /api/sync-domains-progress` - Get sync progress

## 🛠️ Troubleshooting

### Save Button Not Working
- Check browser console for errors
- Verify Flask backend is running on port 5000
- Check network tab for failed requests

### Progress Bar Not Updating
- Progress bar polls every 1 second automatically
- Check if sync operation started successfully
- Verify `/api/sync-domains-progress` endpoint is responding

### Client Auto-fill Not Working
- Ensure clients have URLs configured
- Check if client selection is triggering onChange event
- Verify client data is loaded properly

## 🎯 Why React?

The original Flask template approach had complex JavaScript issues. React provides:

1. **Reliable State Management** - No more lost form data
2. **Component Isolation** - Each feature works independently
3. **Real-time Updates** - Automatic re-rendering when data changes
4. **Better Error Handling** - Clear error messages and recovery
5. **Developer Tools** - Excellent debugging capabilities
6. **Proven Architecture** - Used by millions of applications

This React frontend solves all the issues you experienced with the template-based approach!