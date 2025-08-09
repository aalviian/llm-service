document.addEventListener('DOMContentLoaded', function() {
	const clickBtn = document.getElementById('clickBtn');
	const message = document.getElementById('message');

	clickBtn.addEventListener('click', function() {
		message.textContent = 'Button clicked! JavaScript is working.';
	});
});
