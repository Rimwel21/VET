-- VetSync Database Schema Dump

-- Generated for local PostgreSQL setup


CREATE TABLE contact_messages (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	subject VARCHAR(200), 
	message TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE doctor_availability (
	id SERIAL NOT NULL, 
	date DATE NOT NULL, 
	slot VARCHAR(20) NOT NULL, 
	status VARCHAR(20), 
	PRIMARY KEY (id)
);

CREATE TABLE services (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	icon VARCHAR(10), 
	"desc" TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	first_name VARCHAR(80) NOT NULL, 
	last_name VARCHAR(80) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	contact VARCHAR(30), 
	password_hash VARCHAR(256) NOT NULL, 
	role VARCHAR(20), 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE bookings (
	id SERIAL NOT NULL, 
	service_id INTEGER NOT NULL, 
	slot VARCHAR(20) NOT NULL, 
	date DATE NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	phone VARCHAR(30) NOT NULL, 
	alt_phone VARCHAR(30), 
	address VARCHAR(255), 
	pet_name VARCHAR(80), 
	pet_type VARCHAR(50) NOT NULL, 
	pet_breed VARCHAR(100), 
	pet_sex VARCHAR(30), 
	pet_age VARCHAR(30), 
	pet_weight VARCHAR(20), 
	pet_color VARCHAR(100), 
	visit_reason TEXT, 
	medical_history TEXT, 
	allergies VARCHAR(255), 
	notes TEXT, 
	payment_method VARCHAR(50), 
	consent BOOLEAN, 
	status VARCHAR(20), 
	user_id INTEGER, 
	handled_by VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE notifications (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	message TEXT NOT NULL, 
	read BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE otp_verifications (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	email VARCHAR(120) NOT NULL, 
	otp_code VARCHAR(255) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_used BOOLEAN, 
	attempts INTEGER, 
	reset_token VARCHAR(255), 
	token_expires_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE push_subscriptions (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	endpoint TEXT NOT NULL, 
	p256dh VARCHAR(255) NOT NULL, 
	auth VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE reports (
	id SERIAL NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR(20), 
	admin_comment TEXT, 
	admin_review_status VARCHAR(50), 
	reviewed_by INTEGER, 
	reviewed_at TIMESTAMP WITHOUT TIME ZONE, 
	user_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	is_deleted BOOLEAN, 
	deleted_by INTEGER, 
	deleted_at TIMESTAMP WITHOUT TIME ZONE, 
	edit_history JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(deleted_by) REFERENCES users (id)
);