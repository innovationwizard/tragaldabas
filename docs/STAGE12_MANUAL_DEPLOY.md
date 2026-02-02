# Stage 12 Manual Scaffold & Deploy

This guide walks you through the manual steps to scaffold, migrate, test, and deploy the generated app.
Use it when you want to run Stage 12 yourself without automation.

## 1) Locate the generated app

The scaffolder writes to:

```
${OUTPUT_DIR}/generated-apps/excel-app-<timestamp>
```

Example:

```
./output/generated-apps/excel-app-20250202184512
```

## 2) Install dependencies

```
cd "<generated-app-path>"
npm install
```

## 3) Configure environment variables

Create a `.env` file:

```
DATABASE_URL="file:./prisma/dev.db"
```

If you use Postgres or another provider, replace with the correct connection string.

## 4) Run Prisma migrations

```
npx prisma generate
npx prisma migrate dev --name init
```

## 5) Run tests

```
npm test
```

If you prefer Vitest:

```
npx vitest
```

## 6) Run locally

```
npm run dev
```

Open `http://localhost:3000`.

## 7) Initialize git and commit

```
git init
git add .
git commit -m "Initial generated app"
```

## 8) Push to GitHub

Create a repository and push:

```
git remote add origin <your-repo-url>
git push -u origin main
```

## 9) Deploy to Vercel

Option A: Vercel CLI

```
npm i -g vercel
vercel
```

Option B: Vercel dashboard

1. Import your GitHub repository
2. Add environment variables (DATABASE_URL)
3. Deploy

## 10) Verify

- Create a scenario
- Run a calculation
- Ensure outputs render and validations pass

## Troubleshooting

- **Prisma errors**: Verify `DATABASE_URL` and run `npx prisma migrate dev`.
- **Zod validation**: Ensure input types match schema expectations.
- **Calculation errors**: Check constraints listed in the UI.
