document.addEventListener('DOMContentLoaded', () => {
  const renameForms = document.querySelectorAll('.rename-form');
  const deleteButtons = document.querySelectorAll('.delete-btn');
  const toast = document.getElementById('toast');

  function showToast(message, isSuccess = true) {
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast show ${isSuccess ? 'success' : 'error'}`;
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(() => {
      toast.className = 'toast';
    }, 3000);
  }

  // Handle Rename
  renameForms.forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const jobId = form.getAttribute('data-job-id');
      const input = form.querySelector('input[name="new_name"]');
      const newName = input.value.trim();

      if (!newName) {
        showToast("New name cannot be empty.", false);
        return;
      }

      try {
        input.disabled = true;
        const res = await fetch(`/admin/rename/${jobId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_name: newName })
        });

        const result = await res.json();
        showToast(result.message, res.ok);
        if (res.ok) setTimeout(() => window.location.reload(), 1000);
      } catch (error) {
        showToast("Failed to rename: Network error", false);
      } finally {
        input.disabled = false;
      }
    });
  });

  // Handle Delete
  deleteButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const jobId = button.getAttribute('data-job-id');
      if (!confirm('Are you sure you want to delete this job?')) return;

      try {
        button.disabled = true;
        const res = await fetch(`/admin/delete/${jobId}`, { method: 'DELETE' });
        const result = await res.json();
        showToast(result.message, res.ok);
        if (res.ok) setTimeout(() => window.location.reload(), 1000);
      } catch (error) {
        showToast("Failed to delete: Network error", false);
      } finally {
        button.disabled = false;
      }
    });
  });
});
