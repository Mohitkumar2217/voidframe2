import mongoose from "mongoose";

const ClientSchema = new mongoose.Schema({
  name: String,
  email: { type: String, unique: true },
  password: String, // simple string password
});

const Client = mongoose.model("Client", ClientSchema);
export default Client;
