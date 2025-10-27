# Email Redirection Tool

Bulk email forwarding management for 200+ domains using Namecheap API.

## 🚀 Features

- **Bulk Email Forwarding**: Set email forwarding rules for hundreds of domains at once
- **Namecheap API Integration**: Direct integration with Namecheap's email forwarding API
- **Domain Management**: Import domains from CSV or load directly from your Namecheap account
- **Progress Tracking**: Real-time progress monitoring for bulk operations
- **Results Export**: Export processing results to CSV for record keeping
- **Error Handling**: Comprehensive error handling with detailed logging

## 📋 Prerequisites

1. **Namecheap Account** with API access enabled
2. **API Credentials** from Namecheap
3. **Static IP Address** for API whitelisting
4. **Render.com Account** (or similar hosting platform)

## 🔑 Environment Variables

Set these environment variables in your deployment platform:

```bash
NAMECHEAP_API_USER=your_namecheap_username
NAMECHEAP_API_KEY=your_namecheap_api_key
NAMECHEAP_USERNAME=your_namecheap_username
NAMECHEAP_CLIENT_IP=your_static_ip_address
SECRET_KEY=your-secret-session-key
FLASK_ENV=production
```

## 🌐 Deployment

### Deploy to Render.com

1. **Create Repository**: Push this code to GitHub
2. **Create Web Service**: Connect your GitHub repo to Render
3. **Configure Environment**: Set the required environment variables
4. **Get Static IP**: Note your service's static IP from the dashboard
5. **Whitelist IP**: Add the static IP to your Namecheap API settings

### Local Development

1. Clone the repository
2. Create a `.env` file with your credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`

## 📖 Usage

### Web Interface

1. **Access Dashboard**: Navigate to your deployed URL
2. **Set Forwarding Rules**: Configure email aliases and destinations
3. **Import Domains**: Load domains from CSV or Namecheap account
4. **Bulk Process**: Start bulk email forwarding setup
5. **Monitor Progress**: Track processing status in real-time
6. **Export Results**: Download results CSV when complete

### API Endpoints

- `GET /api/domains` - Get all domains from Namecheap account
- `POST /api/bulk-redirect` - Process bulk email forwarding
- `GET /api/health` - Health check endpoint

## 🔧 Configuration

### Forwarding Rules Format

```json
{
  "forwarding_rules": [
    {"from": "info", "to": "admin@yourmainmail.com"},
    {"from": "contact", "to": "admin@yourmainmail.com"},
    {"from": "support", "to": "support@yourmainmail.com"}
  ]
}
```

### Domain List Format (CSV)

```csv
domain
example.com
test.com
mydomain.org
```

## 🛡️ Security Features

- **IP Whitelisting**: API access restricted to your static IP
- **Secure Sessions**: Flask session management with secure keys
- **Environment Variables**: Sensitive credentials stored securely
- **Error Logging**: Comprehensive logging without exposing credentials

## 📊 Monitoring

The application provides detailed logging for:
- API request/response tracking
- Bulk processing progress
- Error handling and debugging
- Performance metrics

## 🔍 Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check API credentials and IP whitelisting
2. **Connection Timeout**: Verify network connectivity and API endpoint
3. **Rate Limiting**: Namecheap API has rate limits, processing includes delays
4. **Domain Not Found**: Ensure domain is in your Namecheap account

### Debug Mode

Set `FLASK_ENV=development` for detailed error messages and debugging.

## 💰 Cost Estimate

- **Render.com Starter Plan**: $7/month (includes static IP)
- **Namecheap API**: Free with domain registration
- **Total**: ~$7/month for 200+ domain management

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review Namecheap API documentation
3. Check application logs for specific error messages

## 🔄 Updates

This tool is designed for bulk email forwarding operations. For additional features or customizations, modify the Flask application according to your specific needs.