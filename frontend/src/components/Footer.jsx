import './Footer.css'

function Footer() {
  return (
    <footer className="site-footer" id="footer">
      <div className="footer-container">
        <div className="footer-left">
          <span className="footer-brand">SiteGuard</span>
          <span className="footer-divider">•</span>
          <span className="footer-copy">Enterprise Web Intelligence & Uptime Diagnostics</span>
        </div>
        <div className="footer-right">
          <a
            href="https://digitalheroesco.com"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-link"
            id="footer-credit-link"
          >
            Built for Digital Heroes Training Task
          </a>
        </div>
      </div>
    </footer>
  )
}

export default Footer
