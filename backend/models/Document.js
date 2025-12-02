import mongoose from "mongoose";

const DocumentSchema = new mongoose.Schema({
  ownerId: { type: mongoose.Schema.Types.ObjectId, ref: "Client" },
  title: String,
  cloudinaryUrl: String, // store URL after upload
  uploadedAt: { type: Date, default: Date.now }
});

const Document = mongoose.model("Document", DocumentSchema);
export default Document;
