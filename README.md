# Workout WhatsApp Notifier

A Python-based automated workout notification system that sends personalized WhatsApp messages with daily workout plans via Twilio. The system reads workout data from an Excel file and automatically delivers structured workout instructions with exercise links, form cues, and prescriptions.

## Features

- 📱 **WhatsApp Integration**: Send workout notifications via Twilio WhatsApp API
- 📊 **Excel-Based Workout Plans**: Load workout data from customizable Excel files
- 🔄 **Smart Message Chunking**: Automatically splits long messages to comply with Twilio's character limits
- ⏰ **Scheduled Delivery**: Set up automatic daily workout notifications
- 🔗 **Exercise Links**: Includes Google search links to MuscleWiki for exercise demonstrations
- 💡 **Form Cues**: Built-in form tips and technique reminders
- 📋 **Exercise Prescriptions**: Sets, reps, and rest time recommendations
- 🏷️ **Day Aliases**: Send specific workouts using shortcut commands (e.g., `pull1`, `push`, `legs`)
- 🧘 **Warm-up & Cool-down**: Automatic inclusion of appropriate warm-up and cool-down routines

## Prerequisites

- Python 3.7+
- Twilio account with WhatsApp sandbox access
- Excel file with workout plan data

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd workout-notifier
   ```

2. **Install required packages**:
   ```bash
   pip install pandas openpyxl python-dotenv twilio apscheduler pytz
   ```

3. **Set up Twilio WhatsApp**:
   - Create a [Twilio account](https://www.twilio.com/)
   - Access the [WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
   - Note your Account SID, Auth Token, and WhatsApp number
   - Join the sandbox by sending the required message to the Twilio WhatsApp number

4. **Configure environment variables**:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   WHATSAPP_TO_LIST=whatsapp:+91XXXXXXXXXX,whatsapp:+91YYYYYYYYYY
   SEND_TIME_IST=07:00
   ```

## Usage

### Command Line Options

**List available workout aliases**:
```bash
python workout_whatsapp_notifier.py --list-keys
```

**Send today's workout**:
```bash
python workout_whatsapp_notifier.py --send-today
```

**Send specific workout by alias**:
```bash
python workout_whatsapp_notifier.py --send-key pull1
python workout_whatsapp_notifier.py --send-key push
python workout_whatsapp_notifier.py --send-key legs
```

**Send specific workout by day name**:
```bash
python workout_whatsapp_notifier.py --send-day "Day 1 - Pull"
```

**Preview workout message**:
```bash
python workout_whatsapp_notifier.py --preview
```

**Start scheduled daily notifications**:
```bash
python workout_whatsapp_notifier.py --schedule
```

### Excel File Format

The workout plan should be in an Excel file with the following columns:
- `Day`: Workout day name (e.g., "Day 1 - Pull")
- `Exercise`: Exercise name
- `Primary Target`: Primary muscle group
- `Secondary Target`: Secondary muscle group (optional)
- `Tertiary Target`: Tertiary muscle group (optional)

## Workout Categories

The system automatically categorizes workouts based on day names:
- **Pull**: Days containing "pull" (back, biceps, rear delts)
- **Push**: Days containing "push" (chest, shoulders, triceps)
- **Legs**: Days containing "leg" or "legs" (quads, hamstrings, glutes)
- **Cardio**: Days containing "cardio" (HIIT, conditioning)
- **General**: Default category for other workouts

## Built-in Exercise Database

The system includes pre-configured form cues and prescriptions for common exercises:

### Form Cues
- Squat: "Chest tall; knees out; hips back."
- Push Up: "Straight line; don't sag hips."
- Plank: "Hips level; brace core."
- And many more...

### Exercise Prescriptions
- Squats: 3 × 10–12 reps, 90s rest
- Push-ups: 3 × 10–15 reps, 45–60s rest
- Planks: 3 × 30–45s hold, 30s rest
- EMOM exercises for cardio workouts

## Customization

### Adding New Exercises

1. **Form Cues**: Edit the `FORM_CUES` dictionary in the script
2. **Prescriptions**: Edit the `EXERCISE_PRESCRIPTIONS` dictionary
3. **Warm-ups/Cool-downs**: Modify the `WARMUPS` and `COOLDOWNS` dictionaries

### Message Customization

- **Character Limit**: Adjust `MAX_CHARS` environment variable (default: 1500)
- **Time Zone**: Modify the timezone in the `schedule_daily()` function
- **Message Format**: Edit the `build_message_for_day()` function

## File Structure

```
workout-notifier/
├── workout_whatsapp_notifier.py    # Main application script
├── Beginner_Weekly_Workout_Plan.xlsx  # Sample workout plan
├── .env                            # Environment variables (create from env.example)
├── env.example                     # Environment variables template
├── last_day.json                   # State tracking file
├── README.md                       # This file
└── requirements.txt                # Python dependencies (if created)
```

## State Management

The system tracks workout state in `last_day.json`:
- `last_day`: The last workout day that was sent
- `rest_today`: Boolean flag for rest day management

## Troubleshooting

### Common Issues

1. **Twilio Error 21617**: Message too long
   - The system automatically chunks messages, but you can reduce `MAX_CHARS` if needed

2. **WhatsApp not receiving messages**:
   - Ensure you've joined the Twilio WhatsApp sandbox
   - Verify phone number format includes country code
   - Check Twilio console for delivery status

3. **Excel file not found**:
   - Set `WORKOUT_EXCEL_PATH` environment variable to specify custom file location

4. **Scheduling not working**:
   - Ensure the script keeps running for scheduled jobs
   - Check timezone settings in the code

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Required |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Required |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp number | `whatsapp:+14155238886` |
| `WHATSAPP_TO_LIST` | Comma-separated recipient list | Required |
| `SEND_TIME_IST` | Daily send time (24h format) | `07:00` |
| `WORKOUT_EXCEL_PATH` | Path to Excel workout file | `Beginner_Weekly_Workout_Plan.xlsx` |
| `MAX_MESSAGE_CHARS` | Max characters per message | `1500` |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please ensure compliance with Twilio's terms of service when using their API.

## Acknowledgments

- [Twilio](https://www.twilio.com/) for WhatsApp API
- [MuscleWiki](https://musclewiki.com/) for exercise demonstrations
- Exercise form cues and prescriptions based on fitness best practices
