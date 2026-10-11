-- MySQL dump 10.13  Distrib 8.4.11, for Linux (x86_64)
--
-- Host: localhost    Database: datahorse2
-- ------------------------------------------------------
-- Server version	8.4.11

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `caballo`
--

DROP TABLE IF EXISTS `caballo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `caballo` (
  `id_caballo` int NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `sexo` varchar(20) NOT NULL,
  `fecha_nacimiento` date DEFAULT NULL,
  `altura` decimal(5,2) DEFAULT NULL,
  `color` varchar(60) DEFAULT NULL,
  `ubicacion` varchar(180) DEFAULT NULL,
  `descripcion` text,
  `disponibilidad` varchar(30) NOT NULL,
  `raza_id_raza` int NOT NULL,
  `usuario_id_usuario` int NOT NULL,
  PRIMARY KEY (`id_caballo`),
  KEY `fk_caballo_raza_idx` (`raza_id_raza`),
  KEY `fk_caballo_usuario_idx` (`usuario_id_usuario`),
  CONSTRAINT `fk_caballo_raza` FOREIGN KEY (`raza_id_raza`) REFERENCES `raza` (`id_raza`),
  CONSTRAINT `fk_caballo_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `conversacion`
--

DROP TABLE IF EXISTS `conversacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversacion` (
  `id_conversacion` int NOT NULL,
  `fecha_creacion` date NOT NULL,
  `estado` varchar(30) NOT NULL,
  PRIMARY KEY (`id_conversacion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `favorito`
--

DROP TABLE IF EXISTS `favorito`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `favorito` (
  `id_favorito` int NOT NULL,
  `fecha` date NOT NULL,
  `usuario_id_usuario` int NOT NULL,
  `caballo_id_caballo` int NOT NULL,
  PRIMARY KEY (`id_favorito`),
  KEY `fk_favorito_usuario_idx` (`usuario_id_usuario`),
  KEY `fk_favorito_caballo_idx` (`caballo_id_caballo`),
  CONSTRAINT `fk_favorito_caballo` FOREIGN KEY (`caballo_id_caballo`) REFERENCES `caballo` (`id_caballo`),
  CONSTRAINT `fk_favorito_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `foto_caballo`
--

DROP TABLE IF EXISTS `foto_caballo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `foto_caballo` (
  `id_foto` int NOT NULL AUTO_INCREMENT,
  `id_caballo` int NOT NULL,
  `ruta` varchar(500) NOT NULL,
  `es_principal` tinyint(1) NOT NULL DEFAULT '0',
  `orden` int NOT NULL DEFAULT '0',
  `fecha_subida` date DEFAULT NULL,
  PRIMARY KEY (`id_foto`),
  KEY `idx_foto_caballo_id_caballo` (`id_caballo`),
  CONSTRAINT `fk_foto_caballo_caballo` FOREIGN KEY (`id_caballo`) REFERENCES `caballo` (`id_caballo`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mensaje`
--

DROP TABLE IF EXISTS `mensaje`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mensaje` (
  `id_mensaje` int NOT NULL,
  `contenido` text NOT NULL,
  `fecha_envio` date NOT NULL,
  `estado_lectura` varchar(30) NOT NULL,
  `conversacion_id_conversacion` int NOT NULL,
  `usuario_id_usuario` int NOT NULL,
  PRIMARY KEY (`id_mensaje`),
  KEY `fk_mensaje_conversacion_idx` (`conversacion_id_conversacion`),
  KEY `fk_mensaje_usuario_idx` (`usuario_id_usuario`),
  CONSTRAINT `fk_mensaje_conversacion` FOREIGN KEY (`conversacion_id_conversacion`) REFERENCES `conversacion` (`id_conversacion`),
  CONSTRAINT `fk_mensaje_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pedigri`
--

DROP TABLE IF EXISTS `pedigri`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pedigri` (
  `id_pedigri` int NOT NULL,
  `informacion_documento` text,
  `estado_verificacion` varchar(30) NOT NULL,
  `comentario` text,
  `caballo_id_caballo` int NOT NULL,
  PRIMARY KEY (`id_pedigri`),
  KEY `fk_pedigri_caballo_idx` (`caballo_id_caballo`),
  CONSTRAINT `fk_pedigri_caballo` FOREIGN KEY (`caballo_id_caballo`) REFERENCES `caballo` (`id_caballo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `publicacion`
--

DROP TABLE IF EXISTS `publicacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `publicacion` (
  `id_publicacion` int NOT NULL,
  `titulo` varchar(180) NOT NULL,
  `descripcion` text,
  `fecha_publicacion` date NOT NULL,
  `estado` varchar(30) NOT NULL,
  `precio_referencia` decimal(12,2) DEFAULT NULL,
  `caballo_id_caballo` int NOT NULL,
  `usuario_id_usuario` int NOT NULL,
  PRIMARY KEY (`id_publicacion`),
  KEY `fk_publicacion_caballo_idx` (`caballo_id_caballo`),
  KEY `fk_publicacion_usuario_idx` (`usuario_id_usuario`),
  CONSTRAINT `fk_publicacion_caballo` FOREIGN KEY (`caballo_id_caballo`) REFERENCES `caballo` (`id_caballo`),
  CONSTRAINT `fk_publicacion_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `raza`
--

DROP TABLE IF EXISTS `raza`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `raza` (
  `id_raza` int NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text,
  PRIMARY KEY (`id_raza`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resena`
--

DROP TABLE IF EXISTS `resena`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resena` (
  `id_resena` int NOT NULL,
  `calificacion` decimal(2,1) NOT NULL,
  `comentario` text,
  `fecha` date NOT NULL,
  `id_usuario_evaluado` int NOT NULL,
  `id_usuario_evaluador` int NOT NULL,
  PRIMARY KEY (`id_resena`),
  KEY `fk_resena_evaluado_idx` (`id_usuario_evaluado`),
  KEY `fk_resena_evaluador_idx` (`id_usuario_evaluador`),
  CONSTRAINT `fk_resena_evaluado` FOREIGN KEY (`id_usuario_evaluado`) REFERENCES `usuario` (`id_usuario`),
  CONSTRAINT `fk_resena_evaluador` FOREIGN KEY (`id_usuario_evaluador`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resultadocompatibilidad`
--

DROP TABLE IF EXISTS `resultadocompatibilidad`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resultadocompatibilidad` (
  `id_resultado` int NOT NULL,
  `puntuacion` decimal(5,2) NOT NULL,
  `ubicacion_puntos` decimal(5,2) DEFAULT NULL,
  `raza_puntos` decimal(5,2) DEFAULT NULL,
  `madurez_puntos` decimal(5,2) DEFAULT NULL,
  `altura_puntos` decimal(5,2) DEFAULT NULL,
  `otros_puntos` decimal(5,2) DEFAULT NULL,
  `solicitudcompatibilidad_id_solicitud` int NOT NULL,
  `caballo_id_caballo` int NOT NULL,
  PRIMARY KEY (`id_resultado`),
  KEY `fk_resultado_solicitud_idx` (`solicitudcompatibilidad_id_solicitud`),
  KEY `fk_resultado_caballo_idx` (`caballo_id_caballo`),
  CONSTRAINT `fk_resultado_caballo` FOREIGN KEY (`caballo_id_caballo`) REFERENCES `caballo` (`id_caballo`),
  CONSTRAINT `fk_resultado_solicitud` FOREIGN KEY (`solicitudcompatibilidad_id_solicitud`) REFERENCES `solicitudcompatibilidad` (`id_solicitud`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rol`
--

DROP TABLE IF EXISTS `rol`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rol` (
  `id_rol` int NOT NULL,
  `nombre_rol` varchar(80) NOT NULL,
  PRIMARY KEY (`id_rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `solicitudcompatibilidad`
--

DROP TABLE IF EXISTS `solicitudcompatibilidad`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `solicitudcompatibilidad` (
  `id_solicitud` int NOT NULL,
  `fecha` date NOT NULL,
  `resultado` text,
  `usuario_id_usuario` int NOT NULL,
  `caballo_id_caballo` int NOT NULL,
  PRIMARY KEY (`id_solicitud`),
  KEY `fk_solicitud_usuario_idx` (`usuario_id_usuario`),
  KEY `fk_solicitud_caballo_idx` (`caballo_id_caballo`),
  CONSTRAINT `fk_solicitud_caballo` FOREIGN KEY (`caballo_id_caballo`) REFERENCES `caballo` (`id_caballo`),
  CONSTRAINT `fk_solicitud_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usuario`
--

DROP TABLE IF EXISTS `usuario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(120) NOT NULL,
  `correo` varchar(180) NOT NULL,
  `contraseña` varchar(255) NOT NULL,
  `telefono` varchar(30) DEFAULT NULL,
  `ubicacion` varchar(180) DEFAULT NULL,
  `fecha_registro` date NOT NULL,
  `estado` varchar(30) NOT NULL,
  `rol_id_rol` int NOT NULL,
  PRIMARY KEY (`id_usuario`),
  KEY `fk_usuario_rol_idx` (`rol_id_rol`),
  CONSTRAINT `fk_usuario_rol` FOREIGN KEY (`rol_id_rol`) REFERENCES `rol` (`id_rol`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usuario_google`
--

DROP TABLE IF EXISTS `usuario_google`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuario_google` (
  `usuario_id_usuario` int NOT NULL,
  `google_sub` varchar(255) NOT NULL,
  PRIMARY KEY (`usuario_id_usuario`),
  UNIQUE KEY `uq_usuario_google_sub` (`google_sub`),
  CONSTRAINT `fk_usuario_google_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `verificacion_correo`
--

DROP TABLE IF EXISTS `verificacion_correo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `verificacion_correo` (
  `id_verificacion` int NOT NULL AUTO_INCREMENT,
  `usuario_id_usuario` int NOT NULL,
  `codigo_hash` varchar(255) NOT NULL,
  `tipo` varchar(30) NOT NULL,
  `fecha_expiracion` datetime NOT NULL,
  `usado` tinyint(1) NOT NULL DEFAULT '0',
  `intentos` int NOT NULL DEFAULT '0',
  `fecha_creacion` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_verificacion`),
  KEY `fk_verificacion_usuario` (`usuario_id_usuario`),
  CONSTRAINT `fk_verificacion_usuario` FOREIGN KEY (`usuario_id_usuario`) REFERENCES `usuario` (`id_usuario`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'datahorse2'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-11  4:07:00
