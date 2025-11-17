# RAWRE Frontend

React + TypeScript frontend for the RAWRE AI-powered video editing system.

## Features

- **Video Upload**: Drag-and-drop interface for uploading video files
- **Shot Library**: Browse all shots with thumbnails, metadata, and search/filter capabilities
- **AI Compilation**: Configure and start AI-powered edit compilation
- **Real-time Progress**: Live updates during compilation process
- **Shot Selection Visualization**: Selected shots highlighted with red borders and beat numbers
- **Responsive Design**: Modern dark theme optimized for video editing workflows

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Zustand** for state management
- **Axios** for API communication
- **Lucide React** for icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (or configure `VITE_API_URL`)

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Configuration

Create a `.env` file (or copy `.env.example`):

```env
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API client and communication
│   ├── components/    # React components
│   ├── store/         # Zustand state management
│   ├── types/         # TypeScript type definitions
│   ├── App.tsx        # Main application component
│   ├── main.tsx       # Application entry point
│   └── index.css      # Global styles and Tailwind
├── public/            # Static assets
└── index.html         # HTML template
```

## Key Components

### UploadPanel
Handles video file upload with drag-and-drop support and progress tracking.

### ShotLibrary
Displays all shots in a scrollable sidebar with:
- Thumbnail previews
- Shot metadata (type, duration, timecode)
- Search and filter capabilities
- Visual indication of selected shots

### CompilationPanel
Controls for starting AI compilation:
- Quality score threshold
- Start/stop compilation
- Real-time status updates
- Result summary

### ShotThumbnail
Individual shot display with:
- Thumbnail image
- Duration overlay
- Shot type badge
- Beat number (when selected)
- Metadata preview

## State Management

The app uses Zustand for global state management:

- **shots**: Array of all available shots
- **selectedShotIds**: Set of shot IDs selected by AI
- **compilationStatus**: Current compilation progress
- **compilationResult**: Final compilation result
- **aiMessages**: Real-time AI feedback messages

## API Integration

The frontend communicates with the backend API for:

- Uploading and processing videos
- Fetching shot data
- Starting compilation jobs
- Polling compilation status
- Downloading EDL/FCPXML files

## Styling

The app uses Tailwind CSS with a custom dark theme optimized for video editing:

- Dark gray background (`bg-gray-900`)
- Accent colors for different shot types
- Red borders for selected shots
- Smooth transitions and hover effects

## Future Enhancements

- WebSocket support for real-time updates
- Beat timeline visualization
- AI feedback streaming display
- Detailed verification scores panel
- EDL/FCPXML export functionality
- Video preview player
- Advanced shot filtering
- Keyboard shortcuts
