# Glosify

A language learning application with a Spotify-inspired UI for managing vocabulary quizzes and practicing with Anki-style spaced repetition.

## Features

- **Vocabulary Management**: Create quizzes from text, images (OCR), or prompts
- **Smart Extraction**: AI-powered vocabulary extraction with comprehensive word analysis including:
  - Variants (cases, conjugations, etc.)
  - Example sentences with translations
  - Explanations and linguistic properties
  - Support for Ukrainian and Polish languages
- **Anki-Style Practice**: Spaced repetition system (SM-2 algorithm) for both words and sentences
- **Direction-Aware Learning**: Separate tracking for forward (lemma → translation) and reverse (translation → lemma) directions
- **Folder Organization**: Organize quizzes in nested folders
- **Cross-Platform**: React Native app (iOS, Android, Web) with Flask backend

## Tech Stack

### Backend
- Python 3.11
- Flask (REST API)
- SQLAlchemy (ORM)
- SQLite (Database)
- OpenAI GPT-3.5/GPT-4o-mini (Vocabulary extraction and analysis)
- OpenAI GPT-4 Vision (OCR from images)

### Frontend
- React Native (Expo)
- TypeScript
- React Navigation
- Expo Image Picker

## Setup

### Backend

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install flask flask-sqlalchemy flask-login flask-bcrypt flask-cors flask-wtf openai
```

3. Set up the database:
```bash
python init_db.py
```

4. Run migrations (if needed):
```bash
python migrate_languages.py
python migrate_folders.py
python migrate_anki.py
python migrate_anki_directions.py
python migrate_sentence_anki.py
```

5. Create `apikey.txt` with your OpenAI API key (not included in repo)

6. Run the server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend

1. Navigate to the Glosify directory:
```bash
cd Glosify
```

2. Install dependencies:
```bash
npm install
```

3. Update API configuration in `src/api/config.ts` to point to your backend URL

4. Start the Expo development server:
```bash
npm start
# or
npx expo start
```

## Project Structure

```
glosor-webserver/
├── app.py                 # Flask backend application
├── gptcaller.py          # GPT caller for Ukrainian vocabulary
├── gptcaller_polish.py   # GPT caller for Polish vocabulary
├── gptcaller_prompt.py   # GPT caller for prompt-based generation
├── *.py                  # Various utility and model files
├── migrate_*.py          # Database migration scripts
├── tests/                # Test files
├── docs/                 # Documentation
├── instance/             # Database files (gitignored)
└── Glosify/              # React Native frontend
    ├── src/
    │   ├── api/          # API service layer
    │   ├── components/  # React components
    │   ├── context/     # React context (state management)
    │   ├── screens/     # Screen components
    │   ├── types/       # TypeScript type definitions
    │   └── utils/       # Utility functions
    ├── assets/           # App assets (icons, images)
    └── package.json      # Node dependencies
```

## API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - Login
- `GET /api/logout` - Logout
- `GET /api/me` - Get current user

### Quizzes
- `GET /api/quizzes` - Get all quizzes
- `POST /api/quizzes` - Create quiz (supports `prompt` parameter)
- `GET /api/quiz/<id>` - Get quiz details
- `PUT /api/quiz/<id>` - Update quiz/word details
- `DELETE /api/quiz/<id>` - Delete quiz
- `POST /api/quiz/<id>/import-text` - Import text to quiz
- `POST /api/quiz/<id>/import-image` - Import image (OCR) to quiz
- `POST /api/quiz/<id>/cancel-processing` - Cancel background processing

### Folders
- `GET /api/folders` - Get folder tree
- `POST /api/folders` - Create folder
- `POST /api/quiz/<id>/move` - Move quiz to folder

### Anki Practice
- `GET /api/anki/cards` - Get due Anki cards (supports `mode` and `direction` params)
- `GET /api/anki/stats` - Get Anki statistics
- `POST /api/anki/review-word` - Review a word card
- `POST /api/anki/review-sentence` - Review a sentence card

## License

Private project
