import express from "express";
const app = express();
import dotenv from "dotenv";
import documentRoutes from "./routes/documentRoutes.js";
import connectDB from "./config/db.js";
dotenv.config();

app.use(express.json());

// Connect MongoDB
connectDB();

// Routes
app.use("/document", documentRoutes);

app.get("/", (req, res) => {
  res.send("API Running...");
});

app.listen(process.env.PORT, () =>
  console.log(`Server running on port ${process.env.PORT}`)
);
