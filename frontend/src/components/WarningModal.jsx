import { useState } from 'react';

const WARNING_KEY = 'govassist_warning_accepted';

export default function WarningModal() {
  const [visible, setVisible] = useState(
    () => !localStorage.getItem(WARNING_KEY)
  );

  if (!visible) return null;

  const handleConfirm = () => {
    localStorage.setItem(WARNING_KEY, 'true');
    setVisible(false);
  };

  return (
    <div className="modal-overlay">
      <div className="modal" role="dialog" aria-labelledby="warning-title">
        <div className="modal__title" id="warning-title">ご確認ください</div>
        <div className="modal__body">
          <p>本アプリは localhost 限定での使用を前提としています。</p>
          <p>外部ネットワークへの公開は絶対に行わないでください。</p>
        </div>
        <div className="modal__actions">
          <button className="btn btn--primary" onClick={handleConfirm}>
            確認しました
          </button>
        </div>
      </div>
    </div>
  );
}
