/**
 * Navbar.jsx — Top Navigation Bar
 * ==================================
 * Sticky navbar with app branding and gradient logo.
 */

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar__logo">
        <div className="navbar__logo-icon">📈</div>
        <div>
          <div className="navbar__title">AI Trading Assistant</div>
          <div className="navbar__subtitle">Prediction • Sentiment • Reasoning</div>
        </div>
      </div>
      <nav className="navbar__links" aria-label="Dashboard sections">
        <a href="#overview">Overview</a>
        <a href="#market-news">Market News</a>
        <a href="#analysis">Stock Analysis</a>
        <a href="#sentiment">Sentiment</a>
        <a href="#backtest">Backtest</a>
      </nav>
    </nav>
  );
}
