import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginForm() {
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError('アクセストークンを入力してください');
      return;
    }
    setError('');
    setIsLoading(true);
    const success = await login(trimmed);
    setIsLoading(false);
    if (success) {
      navigate('/', { replace: true });
    } else {
      setError('認証トークンが無効です');
    }
  };

  const handleChange = (e) => {
    setToken(e.target.value);
    if (error) setError('');
  };

  return (
    <div className="login-page">
      <div className="card login-page__card">
        <h2>ログイン</h2>
        <p className="login-page__help">
          アクセストークンを入力してください。<br />
          トークンはサーバーの .env ファイルで設定された APP_TOKEN です。
        </p>
        {error && <div className="message message--error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="label" htmlFor="auth-token">アクセストークン</label>
            <input
              id="auth-token"
              className="input"
              type="password"
              value={token}
              onChange={handleChange}
              autoFocus
              disabled={isLoading}
              autoComplete="off"
            />
          </div>
          <button className="btn btn--primary" type="submit" disabled={isLoading}>
            {isLoading ? '認証中...' : 'ログイン'}
          </button>
        </form>
      </div>
    </div>
  );
}
