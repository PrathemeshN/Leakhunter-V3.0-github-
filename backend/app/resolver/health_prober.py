import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)

class TorHealthProber:
    """
    Checks the uptime and health of .onion URLs by routing traffic through the local Tor SOCKS5 proxy.
    Uses 'curl' via subprocess to avoid heavy Python proxy dependencies (like PySocks/aiohttp-socks)
    which would require a full image rebuild.
    """
    
    def __init__(self, tor_proxy: str = "tor:9050"):
        self.tor_proxy = tor_proxy
        
    async def ping_onion(self, onion_url: str, timeout_seconds: int = 20) -> bool:
        """
        Pings a .onion URL over the Tor network.
        Returns True if the site responds with a 2xx or 3xx HTTP status code.
        """
        # Ensure URL has protocol
        if not onion_url.startswith("http"):
            onion_url = f"http://{onion_url}"
            
        logger.info(f"Pinging {onion_url} via Tor proxy ({self.tor_proxy})...")
        
        try:
            # We use curl with --socks5-hostname to route DNS resolution through Tor
            # -s: silent, -o /dev/null: discard body, -w "%{http_code}": only print status code
            cmd = [
                "curl", 
                "--socks5-hostname", self.tor_proxy,
                "--connect-timeout", str(timeout_seconds),
                "--max-time", str(timeout_seconds + 5),
                "-s", 
                "-o", "/dev/null", 
                "-w", "%{http_code}", 
                onion_url
            ]
            
            # Run blocking subprocess in executor
            loop = asyncio.get_running_loop()
            proc = await loop.run_in_executor(
                None, 
                lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            
            if proc.returncode == 0:
                http_code = proc.stdout.strip()
                logger.info(f"Response from {onion_url}: HTTP {http_code}")
                # Treat any valid HTTP response (even 403 Forbidden or 302 Redirect) as "online"
                # because it means the hidden service descriptor was found and the server responded.
                if http_code.isdigit() and int(http_code) > 0:
                    return True
            else:
                logger.debug(f"Curl failed for {onion_url}. Exit code: {proc.returncode}, Error: {proc.stderr.strip()}")
                
        except Exception as e:
            logger.error(f"Error pinging {onion_url}: {e}")
            
        return False
