# Email Redirection Tool - Deployment Guide

## 🌐 Render.com Static IP Addresses

Your available static IPs:
```
44.226.145.213  ← Currently configured in render.yaml
54.187.200.255
34.213.214.55
35.164.95.156
44.230.95.183
44.229.200.200
```

## 🔧 Namecheap API Setup

### Step 1: Enable API Access
1. Log into your Namecheap account
2. Go to Profile → Tools → Namecheap API Access
3. Enable API access if not already enabled
4. Note your API username and generate an API key

### Step 2: Whitelist Static IP
1. In Namecheap API settings, find "Whitelisted IPs"
2. Add this IP address: **44.226.145.213**
3. Save the changes

### Step 3: Test API Connection
You can test your API credentials using this curl command:
```bash
curl "https://api.namecheap.com/xml.response?ApiUser=YOURUSERNAME&ApiKey=YOURAPIKEY&UserName=YOURUSERNAME&Command=namecheap.domains.getList&ClientIp=44.226.145.213"
```

## 🚀 Render.com Deployment

### Step 1: Create New Web Service
1. Go to https://render.com/dashboard
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Choose this repository: `email-redirect-tool`

### Step 2: Configure Build & Deploy Settings
```yaml
Name: email-redirect-tool
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn --bind 0.0.0.0:$PORT app:app
```

### Step 3: Set Environment Variables
In Render dashboard, add these environment variables:

**Required Variables:**
```
NAMECHEAP_API_USER = your_namecheap_username
NAMECHEAP_API_KEY = your_namecheap_api_key  
NAMECHEAP_USERNAME = your_namecheap_username
NAMECHEAP_CLIENT_IP = 44.226.145.213
SECRET_KEY = email-redirect-secure-key-2024-change-in-production
FLASK_ENV = production
```

### Step 4: Deploy
1. Click "Create Web Service"
2. Wait for deployment to complete
3. Note your service URL (e.g., `https://email-redirect-tool.onrender.com`)

## ✅ Testing the Deployment

### 1. Health Check
Visit: `https://your-service-url.onrender.com/api/health`
Expected response:
```json
{
  "status": "healthy",
  "service": "email-redirect-tool",
  "timestamp": "2025-09-11T..."
}
```

### 2. Namecheap API Connection Test
Visit: `https://your-service-url.onrender.com/api/domains`
- Should return your domains from Namecheap
- Or show connection error if credentials are incorrect

### 3. Dashboard Access
Visit: `https://your-service-url.onrender.com/`
- Should show the email redirection dashboard
- Test adding forwarding rules
- Test importing domains

## 🔍 Troubleshooting

### Common Issues:

**1. 401 Unauthorized from Namecheap API:**
- Check API username and key are correct
- Verify IP address is whitelisted: `44.226.145.213`
- Ensure API access is enabled in Namecheap

**2. Connection Timeout:**
- Check if static IP changed in Render
- Verify Namecheap API endpoints are accessible

**3. Environment Variables Not Loading:**
- Check variable names match exactly
- Restart Render service after adding variables
- Check Render logs for startup errors

### Checking Logs:
1. In Render dashboard, go to your service
2. Click "Logs" tab
3. Look for initialization messages and errors

## 🎯 Usage After Deployment

### Bulk Email Forwarding Process:
1. **Access Dashboard**: Visit your Render service URL
2. **Set Forwarding Rules**: Configure email aliases (info, contact, support)
3. **Load Domains**: 
   - Option A: Click "Load Domains from Namecheap" 
   - Option B: Upload CSV with domain list
4. **Preview Changes**: Review what will be configured
5. **Start Processing**: Click "Start Bulk Redirection"
6. **Monitor Progress**: Watch real-time progress bar
7. **Export Results**: Download CSV report when complete

### Example Forwarding Rules:
```
info → admin@yourmainmail.com
contact → admin@yourmainmail.com
support → support@yourmainmail.com
```

## 💰 Costs
- **Render Starter Plan**: $7/month
- **Static IP**: Included
- **Namecheap API**: Free with domains

## 📞 Support
If you encounter issues:
1. Check Render service logs
2. Verify Namecheap API credentials
3. Test with a single domain first
4. Check IP whitelisting in Namecheap