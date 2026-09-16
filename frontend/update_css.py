import re

with open("src/App.css", "r") as f:
    css = f.read()

# Make sidebar glassmorphic
css = re.sub(r'\.sidebar \{[^}]+\}', """.sidebar {
  width: 280px;
  background-color: var(--bg-sidebar);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 32px 20px;
  z-index: 10;
  box-shadow: 4px 0 24px rgba(0,0,0,0.5);
}""", css)

# Make topbar professional
css = re.sub(r'\.topbar \{[^}]+\}', """.topbar {
  height: 80px;
  border-bottom: 1px solid var(--border-color);
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: rgba(6, 9, 14, 0.6);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 5;
}""", css)

# Fix logo
css = re.sub(r'\.logo-icon \{[^}]+\}', """.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--color-primary), #0066ff);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 800;
  font-family: var(--font-header);
  box-shadow: 0 4px 12px rgba(0, 229, 255, 0.4);
}""", css)

# Nav items
css = re.sub(r'\.nav-item \{[^}]+\}', """.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
}""", css)

css = re.sub(r'\.nav-item:hover \{[^}]+\}', """.nav-item:hover {
  background-color: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
  transform: translateX(4px);
}""", css)

# Stat Cards
css = re.sub(r'\.stat-card \{[^}]+\}', """.stat-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-card);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--border-color), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: rgba(255, 255, 255, 0.1);
}
.stat-card:hover::before { opacity: 1; }
""", css)

# Panel cards (charts/feed)
css = re.sub(r'\.panel-card \{[^}]+\}', """.panel-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 28px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  transition: border-color 0.3s ease;
}
.panel-card:hover {
  border-color: rgba(255,255,255,0.1);
}""", css)

# Threat cards
css = re.sub(r'\.threat-card \{[^}]+\}', """.threat-card {
  padding: 20px;
  border-radius: 12px;
  background-color: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.threat-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--border-active);
  transform: scale(1.01);
}""", css)

# Inputs
css = re.sub(r'\.form-group input, \.form-group select \{[^}]+\}', """.form-group input, .form-group select {
  width: 100%;
  padding: 14px 16px;
  background-color: rgba(0,0,0,0.2);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 0.95rem;
  transition: all 0.2s ease;
}
.form-group input:focus, .form-group select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-dim);
}""", css)

# Primary Button
css = re.sub(r'\.btn-primary \{[^}]+\}', """.btn-primary {
  background: linear-gradient(135deg, var(--color-primary), #0088ff);
  color: #000;
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(0, 229, 255, 0.25);
}
.btn-primary:hover {
  box-shadow: 0 6px 20px rgba(0, 229, 255, 0.4);
  transform: translateY(-1px);
  filter: brightness(1.1);
}""", css)

with open("src/App.css", "w") as f:
    f.write(css)

print("CSS updated")
