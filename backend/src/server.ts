import 'reflect-metadata';
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { createConnection } from 'typeorm';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'NetTrace API is running' });
});

// Placeholder for routes
// app.use('/auth', authRoutes);
// app.use('/projects', projectRoutes);
// app.use('/simulations', simulationRoutes);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
