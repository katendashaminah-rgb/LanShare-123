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

  const uploadFiles = async (files) => {
    if (!files || files.length === 0) return;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file, file.name);
      formData.append('folder', 'Documents');

      try {
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || 'Upload failed');
        }
        console.log('Uploaded:', payload);
      } catch (error) {
        console.error('Upload error:', error);
        alert(error.message || 'Upload failed');
      }
    }

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
