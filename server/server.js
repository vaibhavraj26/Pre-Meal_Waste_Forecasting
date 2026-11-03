const express = require('express');
const path = require('path');
const dotenv = require('dotenv');
const { createProxyMiddleware } = require('http-proxy-middleware');

// Load environment variables
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const app = express();
const NODE_PORT = process.env.PORT || process.env.NODE_PORT || 3000;
const PYTHON_PORT = process.env.PYTHON_PORT || 5000;
const PYTHON_API_URL = process.env.PYTHON_API_URL || `http://127.0.0.1:${PYTHON_PORT}`;

// Serve static frontend assets
const publicPath = path.join(__dirname, '..', 'frontend', 'public');
app.use(express.static(publicPath));

// Reverse-proxy /api requests directly to the Python Flask backend
app.use(
  createProxyMiddleware({
    target: PYTHON_API_URL,
    changeOrigin: true,
    pathFilter: '/api',
    onError: (err, req, res) => {
      console.error('[Node Proxy Error] Could not connect to Python backend:', err.message);
      res.status(502).json({
        error: 'Python ML Backend is currently starting or unreachable at ' + PYTHON_API_URL,
        details: err.message
      });
    }
  })
);

// HTML Page Route Handlers for seamless navigation
app.get('/', (req, res) => {
  res.sendFile(path.join(publicPath, 'index.html'));
});

app.get('/predict', (req, res) => {
  res.sendFile(path.join(publicPath, 'predict.html'));
});

app.get('/add-meal', (req, res) => {
  res.sendFile(path.join(publicPath, 'add-meal.html'));
});

app.get('/history', (req, res) => {
  res.sendFile(path.join(publicPath, 'history.html'));
});

app.get('/analytics', (req, res) => {
  res.sendFile(path.join(publicPath, 'analytics.html'));
});

app.get('/model', (req, res) => {
  res.sendFile(path.join(publicPath, 'model.html'));
});

// Fallback 404 handler
app.use((req, res) => {
  res.status(404).sendFile(path.join(publicPath, 'index.html'));
});

// Start Express Server
app.listen(NODE_PORT, () => {
  console.log(`======================================================`);
  console.log(` Smart Mess Food Waste Predictor Web App Running!`);
  console.log(` Web Portal:   http://localhost:${NODE_PORT}`);
  console.log(` Python API:   ${PYTHON_API_URL}`);
  console.log(`======================================================`);
});
