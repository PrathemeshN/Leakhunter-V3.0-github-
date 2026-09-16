const API_BASE_URL = '/api/v1';

export const fetchAuthToken = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });
  if (!response.ok) throw new Error('Invalid credentials');
  return response.json();
};

export const fetchBreaches = async (token) => {
  const response = await fetch(`${API_BASE_URL}/breaches/`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to fetch breaches');
  return response.json();
};

export const fetchStats = async (token) => {
  const response = await fetch(`${API_BASE_URL}/stats`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
};

export const fetchScrapers = async (token) => {
  const response = await fetch(`${API_BASE_URL}/admin/scrapers`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to fetch scrapers');
  return response.json();
};

export const triggerScraper = async (token, name) => {
  const response = await fetch(`${API_BASE_URL}/admin/scrapers/${name}/trigger`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to trigger scraper');
  return response.json();
};
