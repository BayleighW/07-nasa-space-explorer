// Find our date picker inputs on the page
const startInput = document.getElementById('startDate');
const endInput = document.getElementById('endDate');
const getImagesButton = document.getElementById('getImagesButton');
const gallery = document.getElementById('gallery');
const spaceFact = document.getElementById('spaceFact');
const imageModal = document.getElementById('imageModal');
const modalContent = document.getElementById('modalContent');
const closeModalButton = document.getElementById('closeModalButton');

const spaceFacts = [
	'One day on Venus is longer than one year on Venus.',
	'Jupiter has faint rings made mostly of dust.',
	'Footprints left on the Moon can last for millions of years.',
	'Neutron stars can spin hundreds of times every second.',
	'Saturn would float in water because it is less dense than water.'
];

spaceFact.textContent = spaceFacts[Math.floor(Math.random() * spaceFacts.length)];

// Call the setupDateInputs function from dateRange.js
// This sets up the date pickers to:
// - Default to a range of 9 days (from 9 days ago to today)
// - Restrict dates to NASA's image archive (starting from 1995)
setupDateInputs(startInput, endInput);

// Request and display the APOD images for the selected date range
getImagesButton.addEventListener('click', getSpaceImages);

async function getSpaceImages() {
	const startDate = startInput.value;
	const endDate = endInput.value;

	if (!startDate || !endDate || startDate > endDate) {
		gallery.innerHTML = '<p class="placeholder">Choose a valid start and end date.</p>';
		return;
	}

	gallery.innerHTML = '<p class="placeholder">Loading space photos...</p>';
	getImagesButton.disabled = true;

	try {
		const apiUrl = `/api/apod?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`;
		const response = await fetch(apiUrl);
		const data = await response.json();

		if (!response.ok) {
			throw new Error(data.msg || data.error?.message || 'NASA could not return these images.');
		}

		// A one-day request returns one object; a date range returns an array
		const images = Array.isArray(data) ? data : [data];

		if (images.length === 0) {
			gallery.innerHTML = '<p class="placeholder">No space images were found for these dates.</p>';
			return;
		}

		gallery.innerHTML = '';

		images.forEach((item) => {
			const card = document.createElement('article');
			card.className = 'gallery-item';
			card.tabIndex = 0;
			card.setAttribute('role', 'button');
			card.setAttribute('aria-label', `View details for ${item.title}, ${item.date}`);

			if (item.media_type === 'image') {
				const imageUrl = getImageUrl(item);

				if (imageUrl) {
					const image = document.createElement('img');
					image.src = imageUrl;
					image.alt = item.title;
					image.loading = 'lazy';
					image.addEventListener('error', () => {
						image.replaceWith(createUnavailablePreview());
					}, { once: true });
					card.append(image);
				} else {
					card.append(createUnavailablePreview());
				}
			} else {
				const videoMessage = document.createElement('div');
				videoMessage.className = 'video-preview';
				videoMessage.textContent = '▶ Video - select for details';
				card.append(videoMessage);
			}

			const title = document.createElement('h2');
			title.textContent = item.title;

			const date = document.createElement('p');
			date.textContent = item.date;

			card.append(title, date);
			card.addEventListener('click', () => showDetails(item));
			card.addEventListener('keydown', (event) => {
				if (event.key === 'Enter' || event.key === ' ') {
					event.preventDefault();
					showDetails(item);
				}
			});
			gallery.append(card);
		});
	} catch (error) {
		const message = document.createElement('p');
		message.className = 'placeholder';
		message.textContent = `Unable to load space images: ${error.message}`;
		gallery.replaceChildren(message);
	} finally {
		getImagesButton.disabled = false;
	}
}

function showDetails(item) {
	modalContent.innerHTML = '';

	const title = document.createElement('h2');
	title.id = 'modalTitle';
	title.textContent = item.title;

	const date = document.createElement('p');
	date.className = 'modal-date';
	date.textContent = item.date;

	if (item.media_type === 'image') {
		const imageUrl = getImageUrl(item, true);

		if (imageUrl) {
			const image = document.createElement('img');
			image.className = 'modal-image';
			image.src = imageUrl;
			image.alt = item.title;
			image.addEventListener('error', () => {
				image.replaceWith(createArchiveFallback(item.date));
			}, { once: true });
			modalContent.append(image);
		} else {
			modalContent.append(createArchiveFallback(item.date));
		}
	} else {
		const videoMessage = document.createElement('p');
		videoMessage.className = 'video-message';
		videoMessage.textContent = 'This APOD entry is a video.';

		const videoLink = document.createElement('a');
		videoLink.className = 'video-link';
		videoLink.href = item.url;
		videoLink.target = '_blank';
		videoLink.rel = 'noopener noreferrer';
		videoLink.textContent = 'Watch video on NASA';
		modalContent.append(videoMessage, videoLink);
	}

	const explanationTitle = document.createElement('h3');
	explanationTitle.textContent = 'Explanation';

	const explanation = document.createElement('p');
	explanation.className = 'modal-explanation';
	explanation.textContent = item.explanation;

	modalContent.prepend(title, date);
	modalContent.append(explanationTitle, explanation);
	imageModal.showModal();
}

function getImageUrl(item, useHighResolution = false) {
	const imageUrls = useHighResolution ? [item.hdurl, item.url] : [item.url, item.hdurl];
	return imageUrls.find((url) => url && !url.includes('nasa-logo@2x.png'));
}

function createUnavailablePreview() {
	const preview = document.createElement('div');
	preview.className = 'video-preview unavailable-preview';
	preview.textContent = 'Photo unavailable from NASA API - select for original entry';
	return preview;
}

function createArchiveFallback(date) {
	const fallback = document.createElement('div');
	fallback.className = 'image-fallback';

	const message = document.createElement('p');
	message.textContent = 'NASA did not provide a usable photo for this entry.';

	const archiveLink = document.createElement('a');
	const compactDate = date.replaceAll('-', '').slice(2);
	archiveLink.href = `https://apod.nasa.gov/apod/ap${compactDate}.html`;
	archiveLink.target = '_blank';
	archiveLink.rel = 'noopener noreferrer';
	archiveLink.textContent = 'Open the original APOD page';

	fallback.append(message, archiveLink);
	return fallback;
}

closeModalButton.addEventListener('click', () => imageModal.close());

imageModal.addEventListener('click', (event) => {
	if (event.target === imageModal) {
		imageModal.close();
	}
});
