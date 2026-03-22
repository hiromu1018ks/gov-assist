import { useState, useEffect, useRef } from 'react';

const MESSAGES = [
  'All systems operational.',
  'Firewall: ACTIVE (localhost only)',
  'Coffee level: CRITICAL',
  'There is no place like 127.0.0.1',
  'SSH connection secure. Probably.',
  'AI model loaded. Skynet is not activated.',
  'Remember: with great power comes great responsibility',
  'rm -rf /boredom',
  'Document processed: 0 errors found',
  'Uptime: calculating...',
  'Token budget: sufficient',
  'No backdoors found. Yet.',
];

const INTERVAL_MS = 5000;

export default function useStatusMessages() {
  const [message, setMessage] = useState(MESSAGES[0]);
  const indexRef = useRef(0);

  useEffect(() => {
    const timer = setInterval(() => {
      indexRef.current = (indexRef.current + 1) % MESSAGES.length;
      setMessage(MESSAGES[indexRef.current]);
    }, INTERVAL_MS);

    return () => clearInterval(timer);
  }, []);

  return message;
}
