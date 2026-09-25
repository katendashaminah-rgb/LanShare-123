document.addEventListener('DOMContentLoaded', () => {
  const updateStorage = async () => {
    try {
      const response = await fetch('/api/status');
      const data = await response.json();
      const usedGB = (data.storage_used / 1000000000).toFixed(1);
      const totalGB = (data.storage_limit / 1000000000).toFixed(0);
      const percent = Math.min(100, Math.max(0, (data.storage_used / data.storage_limit) * 100));

      const storageReadout = document.getElementById('storage-readout');
      const storageSummary = document.getElementById('storage-summary');
      const storageBar = document.getElementById('storage-bar');
      if (storageReadout) storageReadout.textContent = `${usedGB} GB / ${totalGB} GB`;
      if (storageSummary) storageSummary.textContent = `${percent.toFixed(0)}% used`;
      if (storageBar) storageBar.style.width = `${percent}%`;
    } catch (error) {
      console.error('Storage update failed', error);
    }
  };

  const loadDevices = async () => {
    try {
      const response = await fetch('/api/discover');
      const data = await response.json();
      const list = document.getElementById('lan-devices');
      if (!list) return;
      list.innerHTML = '';
      for (const device of data.devices || []) {
        const item = document.createElement('li');
        item.textContent = `${device.device_name} (${device.ip_address})`;
        list.appendChild(item);
      }
    } catch (error) {
      console.error('Device discovery failed', error);
    }
  };

  const listRemoteFiles = async (deviceIp) => {
    try {
      const response = await fetch(`/api/remote/files?device_ip=${encodeURIComponent(deviceIp)}`);
      const data = await response.json();
      const table = document.getElementById('file-table-body');
      if (!table) return;
      table.innerHTML = '';
      for (const item of data.items || []) {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>📄</td>
          <td>${item.name}</td>
          <td>${item.type || 'file'}</td>
          <td>${item.size}</td>
          <td>Now</td>
          <td>
            <button data-device-ip="${deviceIp}" data-path="${item.path}" class="download-remote">Download</button>
          </td>
        `;
        table.appendChild(row);
      }

      document.querySelectorAll('.download-remote').forEach((button) => {
        button.addEventListener('click', async () => {
          const deviceIp = button.dataset.deviceIp;
          const path = button.dataset.path;
          const response = await fetch(`/api/remote/download?device_ip=${encodeURIComponent(deviceIp)}&path=${encodeURIComponent(path)}`);
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.error || 'Remote download failed');
          }
          alert(`Downloaded to ${payload.path}`);
        });
      });
    } catch (error) {
      console.error('Remote file listing failed', error);
    }
  };

  const loadLocalFiles = async () => {
    try {
      const response = await fetch('/api/files');
      const data = await response.json();
      const table = document.getElementById('file-table-body');
      if (!table) return;
      table.innerHTML = '';
      for (const item of data.items || []) {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>📄</td>
          <td>${item.name}</td>
          <td>${item.type || 'file'}</td>
          <td>${item.size}</td>
          <td>Now</td>
          <td>
            <a href="/api/download/${encodeURIComponent(item.path)}" target="_blank">Download</a>
            <button data-path="${item.path}" class="delete-local">Delete</button>
          </td>
        `;
        table.appendChild(row);
      }

      document.querySelectorAll('.delete-local').forEach((button) => {
        button.addEventListener('click', async () => {
          const path = button.dataset.path;
          const response = await fetch('/api/files', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.error || 'Delete failed');
          }
          loadLocalFiles();
        });
      });
    } catch (error) {
      console.error('Local file loading failed', error);
    }
  };

  const uploadFile = (file, onProgress) => new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file, file.name);
    formData.append('folder', 'Documents');

    const request = new XMLHttpRequest();
    request.open('POST', '/api/upload');
    request.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener('load', () => {
      let payload;
      try {
        payload = JSON.parse(request.responseText);
      } catch (error) {
        reject(new Error('The server returned an invalid upload response.'));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(payload.error || 'Upload failed'));
        return;
      }
      resolve(payload);
    });
    request.addEventListener('error', () => reject(new Error('The upload could not reach the server.')));
    request.addEventListener('abort', () => reject(new Error('Upload cancelled.')));
    request.send(formData);
  });

  const uploadFiles = async (files) => {
    if (!files || files.length === 0) return;

    const status = document.getElementById('upload-status');
    const statusText = document.getElementById('upload-status-text');
    const progressValue = document.getElementById('upload-progress-value');
    const uploadList = document.getElementById('upload-list');
    const uploadButton = document.getElementById('upload-button');
    if (status) status.hidden = false;
    if (uploadButton) uploadButton.disabled = true;
    if (uploadList) uploadList.innerHTML = '';

    const items = Array.from(files).map((file) => {
      const item = document.createElement('li');
      item.className = 'upload-item';
      item.innerHTML = `
        <div class="upload-item-header">
          <span class="upload-state-icon">...</span>
          <div class="upload-file-details"><strong></strong><small>Queued</small></div>
          <span class="upload-item-percent">0%</span>
        </div>
        <div class="upload-progress-track"><div class="upload-progress"></div></div>
        <div class="upload-location"></div>
      `;
      item.querySelector('strong').textContent = file.name;
      uploadList?.appendChild(item);
      return {
        file,
        item,
        state: item.querySelector('.upload-file-details small'),
        icon: item.querySelector('.upload-state-icon'),
        percent: item.querySelector('.upload-item-percent'),
        progress: item.querySelector('.upload-progress'),
        location: item.querySelector('.upload-location'),
      };
    });

    let processed = 0;
    let succeeded = 0;
    let failed = 0;
    const updateSummary = () => {
      if (statusText) {
        statusText.textContent = processed === items.length
          ? (failed ? 'Uploads finished with errors' : 'Uploads complete')
          : `Uploading ${processed + 1} of ${items.length}`;
      }
      if (progressValue) progressValue.textContent = `${succeeded} uploaded${failed ? `, ${failed} failed` : ''}`;
    };
    updateSummary();

    for (const upload of items) {
      const { file, state, icon, percent, progress, location } = upload;
      try {
        state.textContent = 'Uploading';
        icon.textContent = '↑';
        upload.item.classList.add('is-uploading');
        const payload = await uploadFile(file, (percent) => {
          progress.style.width = `${percent}%`;
          upload.item.querySelector('.upload-item-percent').textContent = `${percent}%`;
        });
        state.textContent = 'Uploaded';
        icon.textContent = '✓';
        percent.textContent = '100%';
        progress.style.width = '100%';
        location.textContent = `Saved to ${payload.relative_path}`;
        upload.item.classList.remove('is-uploading');
        upload.item.classList.add('is-complete');
        succeeded += 1;
      } catch (error) {
        console.error('Upload error:', error);
        state.textContent = 'Could not upload';
        icon.textContent = '!';
        location.textContent = error.message || 'Upload failed';
        upload.item.classList.remove('is-uploading');
        upload.item.classList.add('is-failed');
        failed += 1;
      }
      processed += 1;
      updateSummary();
    }

    if (uploadButton) uploadButton.disabled = false;
    updateStorage();
    loadLocalFiles();
  };

  const uploadButton = document.getElementById('upload-button');
  const uploadInput = document.getElementById('upload-input');
  if (uploadButton && uploadInput) {
    uploadButton.addEventListener('click', () => uploadInput.click());
    uploadInput.addEventListener('change', (event) => {
      uploadFiles(event.target.files);
      uploadInput.value = '';
    });
  }

  const folderButton = document.getElementById('new-folder-button');
  if (folderButton) {
    folderButton.addEventListener('click', async () => {
      const name = window.prompt('Folder name');
      if (!name) return;
      try {
        const response = await fetch('/api/folders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Folder creation failed');
        alert('Folder created');
      } catch (error) {
        console.error('Folder error:', error);
        alert(error.message || 'Folder creation failed');
      }
    });
  }

  const deviceList = document.getElementById('device-list');
  if (deviceList) {
    const refreshDevices = async () => {
      try {
        const response = await fetch('/api/discover');
        const data = await response.json();
        deviceList.innerHTML = '';
        for (const device of data.devices || []) {
          const card = document.createElement('div');
          card.className = 'device-card';
          card.innerHTML = `
            <h3>${device.device_name}</h3>
            <p>${device.ip_address}:${device.port}</p>
            <button data-device-ip="${device.ip_address}" class="browse-device">Browse</button>
          `;
          deviceList.appendChild(card);
        }

        document.querySelectorAll('.browse-device').forEach((button) => {
          button.addEventListener('click', async () => {
            const ip = button.dataset.deviceIp;
            await listRemoteFiles(ip);
          });
        });
      } catch (error) {
        console.error('Device discovery failed', error);
      }
    };

    const refreshButton = document.getElementById('refresh-devices');
    if (refreshButton) refreshButton.addEventListener('click', refreshDevices);
    refreshDevices();
  }

  if (document.getElementById('file-table-body')) {
    loadLocalFiles();
  }

  updateStorage();
  loadDevices();
  const refresh = document.getElementById('refresh-devices');
  if (refresh) refresh.addEventListener('click', loadDevices);
});
