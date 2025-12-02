import mongoose from "mongoose";

const AdminSchema = new mongoose.Schema({
  name: String,
  email: { type: String, unique: true },
  password: String, // simple string password
});

const Admin = mongoose.model("Admin", AdminSchema);
export default Admin;
